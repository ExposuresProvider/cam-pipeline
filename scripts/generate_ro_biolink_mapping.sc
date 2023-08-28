//> using scala "2.13"
//> using dep "dev.zio::zio:2.0.16"
//> using dep "dev.zio::zio-streams:2.0.16"
//> using dep "dev.zio::zio-json:0.6.1"
//> using dep "io.circe::circe-core:0.14.5"
//> using dep "io.circe::circe-generic:0.14.5"
//> using dep "io.circe::circe-parser:0.14.5"
//> using dep "io.circe::circe-yaml:0.14.2"
//> using dep "com.typesafe.scala-logging::scala-logging:3.9.5"
//> using dep "ch.qos.logback:logback-classic:1.4.11"

import scala.io._

import java.io._

import zio._
import zio.Console._
import zio.stream._
import zio.json._
import com.typesafe.scalalogging._

import io.circe.syntax._
import io.circe.generic.auto._


/**
 * In order for these PredicateMappings to make sense in Biolink, we need to map
 * them into the format that is needed for a TRAPIEdge, which is a list of TRAPIQualifiers.
 */
case class TRAPIQualifier(qualifierTypeId: String, qualifierValue: String) {
  // Some day I will get io.circe.syntax._ to work so we can emit JSON, but it is not this day.
  override val toString = s"""{"${qualifierTypeId}":"${qualifierValue}"}"""
}


/**
 * CAM-Pipeline (including the CAMs and the relevant ontologies) express relations between concepts using predicates
 * from the Relation Ontology (RO). When we provide these edges to Orion, we need to do so as qualified Biolink
 * predicates. This Scala CLI script will generate a mapping file that provides information on how RO predicates
 * should be mapped to Biolink predicates with qualifiers.
 *
 * To generate this file, this Scala CLI script will read predicates from three sources:
 * 1. From the list of Biolink predicates [1], some of which have exact/broad/narrow mappings to RO terms.
 * 2. From the list of predicate mappings [2], which has qualified predicates (some of which are mapped to RO terms).
 * 3. From any additional manual mappings, which we currently write down in this file. These should be moved into the
 *    two Biolink files [1][2].
 *
 * [1] https://github.com/biolink/biolink-model/blob/68d4e3d7612275d0d7e832a9919bf8666e1d5fde/biolink-model.yaml#L1643
 * [2] https://github.com/biolink/biolink-model/blob/68d4e3d7612275d0d7e832a9919bf8666e1d5fde/predicate_mapping.yaml
 */

object ROBiolinkMappingsGenerator extends ZIOAppDefault with LazyLogging {
  /*
   * Some manual annotations (we should try to move these into Biolink model so we don't need to deal with them ourselves.
   */
  val manualPredicateMappingRows = Seq(
    PredicateMappingRow(
      predicate = "biolink:regulates", // Is this the best one?
      `mapped predicate` = None,
      `object aspect qualifier` = None,
      `object direction qualifier` = Some("downregulated"),
      `qualified predicate` = None,
      `exact matches` = Some(Set("RO:0002305")), // causally upstream of, negative effect
    ),
    PredicateMappingRow(
      predicate = "biolink:regulates", // Is this the best one?
      `mapped predicate` = None,
      `object aspect qualifier` = None,
      `object direction qualifier` = Some("upregulated"),
      `qualified predicate` = None,
      `exact matches` = Some(Set("RO:0002304")), // causally upstream of, positive effect
    )
  )

  /* Configuration for this generator */
  final case class Conf(
                   outputFilename: String,
                   biolinkVersion: String = "v3.5.4",
                   localMappingsFilename: String = "ro-to-biolink-local-mappings.tsv"
                 )

  /** Overall code for running this generator. */
  override def run = for {
    conf <- readCommandLineArgs
    _ = logger.info(s"Output filename: ${conf.outputFilename}")

    _ = logger.info(s"Loaded ${manualPredicateMappingRows.length} manually curated predicate mapping rows.")

    // Load local mappings.
    localMappings <- readLocalMappings(new File(conf.localMappingsFilename))
    _ = logger.info(s"Loaded ${localMappings.size} local mappings.")

    // githubBiolinkModel <- getPredicateMappingsFromBiolinkModel(conf)
    githubPredicateMappings <- getPredicateMappingsFromGitHub(conf)
    _ = logger.info(s"Loaded ${githubPredicateMappings.length} mappings from the predicate mappings file.")

    outputPredicates: Seq[PredicateMappingRow] = githubPredicateMappings ++ manualPredicateMappingRows

    // Check for unusual predicates.
    warnings = checkMappings(localMappings, outputPredicates)

    _ = if(warnings.nonEmpty) {
      logger.warn(s"Found ${warnings.size} mapping warnings:")
      warnings.foreach(warning => logger.warn(s" - ${warning}"))
    }

    countPredsWritten <- writePredicates(outputPredicates, conf.outputFilename)
    _ = logger.info(s"Wrote out ${countPredsWritten} to ${conf.outputFilename}.")
  } yield ()

  /**
   * Write the predicates into a tab-delimited file.
   *
   * @param predicates An Iterable of the predicates to write (as PredicateMappingRows)
   * @param outputFilename The output filename to write to.
   * @return A ZIO that resolves to an integer that indicates the number of predicates written out.
   */
  def writePredicates(predicates: Iterable[PredicateMappingRow], outputFilename: String): RIO[Scope, Int] = for {
    outputFile <- ZIO.acquireRelease(ZIO.attemptBlockingIO(new FileWriter(outputFilename)))(fw => ZIO.succeedBlocking(fw.close()))
    _ = outputFile.write("mapping_type\tpredicate\tbiolink_predicate\t" +
      // "object_aspect_qualifier\tobject_direction_qualifier\tqualified_predicate\t" +
      "qualifier_set\n")
  } yield {
    predicates
      .foreach(predicate => {
        def writePredicatesOfMappingType(mappingType: String, predicateId: String, predicateMappingRow: PredicateMappingRow) = {
          // We're only interested in RO: predicates for now, and to simplify things, we'll expand them.
          val predicateURL = if (predicateId.startsWith("RO:")) {
            "<http://purl.obolibrary.org/obo/RO_" + predicateId.substring(3) + ">"
          } else if (predicateId.startsWith("GOREL:")) {
            "<http://purl.obolibrary.org/obo/GOREL_" + predicateId.substring(6) + ">"
          } else {
            predicateId
          }

          val biolinkPredicateURL = if(predicateMappingRow.predicate.startsWith("biolink:"))
            "<https://w3id.org/biolink/vocab/" + predicateMappingRow.predicate.substring(8) + ">"
          else predicateMappingRow.predicate

          if (predicateURL.startsWith("<"))
            outputFile.write(
              s"${mappingType}\t${predicateURL}\t${biolinkPredicateURL}\t" +
                // s"${predicateMappingRow.`object aspect qualifier`.getOrElse("")}\t${predicateMappingRow.`object direction qualifier`.getOrElse("")}\t${predicateMappingRow.`qualified predicate`.getOrElse("")}\t" +
                s"${predicateMappingRow.asQualifierList.mkString("||")}\n")
        }

        // Write out all four possible types.
        predicate.`exact matches`.getOrElse(Set()).foreach(writePredicatesOfMappingType("exact", _, predicate))
        predicate.`close matches`.getOrElse(Set()).foreach(writePredicatesOfMappingType("close", _, predicate))
        predicate.`broad matches`.getOrElse(Set()).foreach(writePredicatesOfMappingType("broad", _, predicate))
        predicate.`narrow matches`.getOrElse(Set()).foreach(writePredicatesOfMappingType("narrow", _, predicate))
    })
    predicates.size
  }

  /**
   * We might need to set up more complex command line parsing later, but for now we only have a single argument
   * that is the output filename, so that's all we need to submit.
   */
  val readCommandLineArgs: ZIO[ZIOAppArgs, Throwable, Conf] = for {
    args <- getArgs
    outputFilename <- ZIO.fromOption(args.headOption).orElseFail(new RuntimeException(
      "One argument required: first argument should be filename to write mappings to."
    ))
  } yield {
    Conf(
      outputFilename = outputFilename
    )
  }

  /* Code taken from https://zio.dev/reference/resource/scope */
  def acquireSourceByURL(url: => String): ZIO[Any, IOException, Source] =
    ZIO.attemptBlockingIO(Source.fromURL(url))

  def acquireSourceByFile(file: => File): ZIO[Any, IOException, Source] =
    ZIO.attemptBlockingIO(Source.fromFile(file))

  def releaseSource(source: => Source): ZIO[Any, Nothing, Unit] =
    ZIO.succeedBlocking(source.close())

  /** A ZIO wrapper for scala Sources. */
  def sourceForURL(url: => String): ZIO[Scope, IOException, Source] =
    ZIO.acquireRelease(acquireSourceByURL(url))(releaseSource(_))

  def sourceForFile(file: => File): ZIO[Scope, IOException, Source] =
    ZIO.acquireRelease(acquireSourceByFile(file))(releaseSource(_))

  /** A case class for predicate mappings from the Biolink predicate_mappings.yaml file [1].
   *
   * [1] https://github.com/biolink/biolink-model/blob/68d4e3d7612275d0d7e832a9919bf8666e1d5fde/predicate_mapping.yaml
   */
  case class PredicateMappingRow(
                                  `mapped predicate`: Option[String],
                                  `object aspect qualifier`: Option[String],
                                  `object direction qualifier`: Option[String],
                                  predicate: String,
                                  `qualified predicate`: Option[String],
                                  `exact matches`: Option[Set[String]],
                                  `close matches`: Option[Set[String]] = None,
                                  `broad matches`: Option[Set[String]] = None,
                                  `narrow matches`: Option[Set[String]] = None
                                ) {

    val asQualifierList: List[TRAPIQualifier] = {
      (
        `qualified predicate`.map(q => List(TRAPIQualifier("biolink:qualified_predicate", q))) ++
        `object aspect qualifier`.map(q => List(TRAPIQualifier("biolink:object_aspect_qualifier", q))) ++
        `object direction qualifier`.map(q => List(TRAPIQualifier("biolink:object_direction_qualifier", q)))
      )
        .flatten.toList
    }

    /** Return a list of all RO terms in this predicate mapping row. */
    val roTerms: Set[String] = (`exact matches` ++ `close matches` ++ `broad matches` ++ `narrow matches`).flatten.toSet
  }

  /** Since the predicate mappings file consists of a top level `predicate mappings` element, we need to
   * replicate that in order to be able to read it. */
  case class PredicateMappings(
                                `predicate mappings`: List[PredicateMappingRow]
                              )

  /**
   * Download the Biolink Model and extract predicates from it.
   *
   * We don't currently use this, as the mappings in ./ro-to-biolink-local-mappings.tsv are
   * the manually curated mappings we prefer. But I'm going to leave this code here in case
   * it becomes useful in the future.
   *
   * @param conf The configuration settings to use.
   * @return A RIO resolving to a list of PredicateMappingRows.
   */
  def getPredicateMappingsFromBiolinkModel(conf: Conf): RIO[Scope, List[PredicateMappingRow]] =
    for {
      biolinkModelText <-
        sourceForURL(s"https://raw.githubusercontent.com/biolink/biolink-model/${conf.biolinkVersion}/biolink-model.yaml")
          .flatMap(source => {
              ZIO.attemptBlockingIO(source.getLines().mkString("\n"))
          })
      biolinkModelYaml <- ZIO.fromEither(io.circe.yaml.parser.parse(biolinkModelText))
      biolinkModelCursor = biolinkModelYaml.hcursor
      slotsCursor = biolinkModelCursor.downField("slots")
      slots = slotsCursor.keys.getOrElse(List())
      roMappings = slots.toList.map(slot => {
          val slotCursor = slotsCursor.downField(slot)

          val exactMappings = slotCursor.downField("exact_mappings").as[List[String]].getOrElse(List())
          val closeMappings = slotCursor.downField("close_mappings").as[List[String]].getOrElse(List())
          val broadMappings = slotCursor.downField("broad_mappings").as[List[String]].getOrElse(List())
          val narrowMappings = slotCursor.downField("narrow_mappings").as[List[String]].getOrElse(List())

        /*
          val mappings = exactMappings.map(m => ("exact", m)) ++
            closeMappings.map(m => ("close", m)) ++
            broadMappings.map(m => ("broad", m)) ++
            narrowMappings.map(m => ("narrow", m))

         */

          // mappings
            // .filter({ case (_, mapp) => mapp.startsWith("RO:") })
            // .map({ case (mtype, mapp) => (mtype, "http://purl.obolibrary.org/obo/RO_" + mapp.substring(3)) })

          PredicateMappingRow(
              `mapped predicate` = None,
              `object aspect qualifier` = None,
              `object direction qualifier` = None,
              predicate = "biolink:" + slot.replace(' ', '_'),
              `qualified predicate` = None,
              `exact matches` = Some(exactMappings.toSet),
              `close matches` = Some(closeMappings.toSet),
              `broad matches` = Some(broadMappings.toSet),
              `narrow matches` = Some(narrowMappings.toSet)
            )
          })
    } yield roMappings

  /**
   * Download the predicate_mapping.yaml file for the Biolink model specified in the configuration.
   *
   * @param conf Configuration to use.
   * @return A RIO resolving to a list of predicate mapping rows.
   */
  def getPredicateMappingsFromGitHub(conf: Conf): RIO[Scope, List[PredicateMappingRow]] =
    for {
      predicateMappingText <-
        sourceForURL(s"https://raw.githubusercontent.com/biolink/biolink-model/${conf.biolinkVersion}/predicate_mapping.yaml")
          .flatMap(source => {
            ZIO.attemptBlockingIO(source.getLines().mkString("\n"))
          })
      predicateMappingsYaml <- ZIO.fromEither(io.circe.yaml.parser.parse(predicateMappingText))
      predicateMappings <- ZIO.fromEither(predicateMappingsYaml.as[PredicateMappings])
      mappings = predicateMappings.`predicate mappings`
    } yield {
      mappings.map(mapping =>
        PredicateMappingRow(
          `mapped predicate` = mapping.`mapped predicate`,
          `object aspect qualifier` = mapping.`object aspect qualifier`,
          `object direction qualifier` = mapping.`object direction qualifier`,
          predicate = "biolink:" + mapping.predicate.replace(' ', '_'),
          `qualified predicate` = mapping.`qualified predicate`.map(qp => "biolink:" + qp.replace(' ', '_')),
          `exact matches` = mapping.`exact matches`,
          `close matches` = mapping.`close matches`,
          `broad matches` = mapping.`broad matches`,
          `narrow matches` = mapping.`narrow matches`
        )
      )
    }

  /**
   * A case class to hold local mappings.
   *
   * @param roTerm The RO term being mapped. (May also be from another ontology.)
   * @param biolinkTerm The Biolink term being mapped to.
   * @param mappingType The mapping type ("exact", "close", "broad", "narrow").
   */
  case class SimpleMapping(
      roTerm: String,
      biolinkTerm: String,
      mappingType: String
                          )

  /**
   * Read local mappings from the `ro-to-biolink-local-mappings.tsv` file as PredicateMappingRow entries.
   *
   * @param localMappingFile The local mapping TSV file to read.
   */
  def readLocalMappings(localMappingFile: File): RIO[Scope, List[SimpleMapping]] = for {
    localMappingsLines <-
      sourceForFile(localMappingFile)
        .flatMap(source => {
          ZIO.attemptBlockingIO(source.getLines())
        })
    predMappings <- ZStream.fromIterator(localMappingsLines).mapZIO(mappingLine => {
      val values = mappingLine.split('\t')

      val roTerm = values(0) match {
        case s"<http://purl.obolibrary.org/obo/BFO_${id}>" => s"BFO:${id}"
        case s"<http://purl.obolibrary.org/obo/GOREL_${id}>" => s"GOREL:${id}"
        case s"<http://purl.obolibrary.org/obo/RO_${id}>" => s"RO:${id}"
        case s"<http://purl.obolibrary.org/obo/UPHENO_${id}>" => s"UPHENO:${id}"
        case s"<http://purl.obolibrary.org/obo/emapa#${id}>" => s"emapa:${id}"
        case _ => return ZIO.fail(new RuntimeException(s"Expected RO term but got ${values(0)} instead."))
      }

      // TODO: we should really use the Biolink predicate code from CAM-KP for this part.
      val biolinkTerm = values(1) match {
        case s"<https://w3id.org/biolink/vocab/${id}>" => s"biolink:${id}"
        case _ => return ZIO.fail(new RuntimeException(s"Expected Biolink term but got ${values(1)} instead."))
      }

      values(2) match {
        case "exact" | "close" | "broad" | "narrow" => ZIO.succeed(SimpleMapping(
          roTerm = roTerm,
          biolinkTerm = biolinkTerm,
          mappingType = values(2)
        ))
        case _ => ZIO.fail(new RuntimeException(s"Expected mapping type but got ${values(2)} instead."))
      }
    }).runCollect
  } yield predMappings.toList

  /**
   * A method to generate a list of warnings about the mappings.
   *
   * @param localMappings The list of local mappings. These are manually curated and
   * @param outputPredicates The list of predicates generated by this program. This should not overlap with the local
   *                         mappings already in use -- if they do, we'll get duplicate entries in the output!
   * @return A list of warnings as strings (we can turn this into a case class if needed).
   */
  def checkMappings(localMappings: Seq[SimpleMapping], outputPredicates: Seq[PredicateMappingRow]): Seq[String] = {

    val localDuplicateWarnings = localMappings.groupBy(_.roTerm).collect {
      case (roTerm, occurrences) if occurrences.length > 1 => (roTerm, occurrences.map(_.biolinkTerm))
    }.map(t => s"Local mapping file maps ${t._1} to multiple Biolink terms: ${t._2}")

    val outputPredicatesByROTerms = outputPredicates.flatMap(op => op.roTerms.map(ro => (ro, op)))
      .groupBy(_._1)
      .collect {
        case (roTerm, occurrences) if occurrences.length > 1 => (roTerm, occurrences.map(_._2))
      }
    val predicateMappingsDuplicateWarnings = outputPredicatesByROTerms.map(t => s"Generated predicate mapping file maps ${t._1} to multiple Biolink terms: ${t._2}")

    val localMappingsAsPredicateMappings = localMappings.map(localMapping => {
      localMapping.mappingType match {
        case "exact" => PredicateMappingRow(
          predicate = localMapping.biolinkTerm,
          `mapped predicate` = None,
          `object aspect qualifier` = None,
          `object direction qualifier` = None,
          `qualified predicate` = None,
          `exact matches` = Some(Set(localMapping.roTerm))
        )
        case "close" => PredicateMappingRow(
          predicate = localMapping.biolinkTerm,
          `mapped predicate` = None,
          `object aspect qualifier` = None,
          `object direction qualifier` = None,
          `qualified predicate` = None,
          `exact matches` = None,
          `close matches` = Some(Set(localMapping.roTerm))
        )
        case "broad" => PredicateMappingRow(
          predicate = localMapping.biolinkTerm,
          `mapped predicate` = None,
          `object aspect qualifier` = None,
          `object direction qualifier` = None,
          `qualified predicate` = None,
          `exact matches` = None,
          `broad matches` = Some(Set(localMapping.roTerm))
        )
        case "narrow" => PredicateMappingRow(
          predicate = localMapping.biolinkTerm,
          `mapped predicate` = None,
          `object aspect qualifier` = None,
          `object direction qualifier` = None,
          `qualified predicate` = None,
          `exact matches` = None,
          `narrow matches` = Some(Set(localMapping.roTerm))
        )
        case _ => throw new RuntimeException(s"Unknown mapping type: ${localMapping.mappingType}, expected 'exact', 'close', 'broad', 'narrow'.")
      }
    })
    val allMappingsByROTerms = (localMappingsAsPredicateMappings ++ outputPredicates).flatMap(op => op.roTerms.map(ro => (ro, op)))
      .groupBy(_._1)
      .collect {
        case (roTerm, occurrences) if occurrences.length > 1 => (roTerm, occurrences.map(_._2))
      }

    val allMappingsDuplicateWarnings = allMappingsByROTerms.map(t => s"Combined predicate mappings maps ${t._1} to multiple Biolink terms: ${t._2}")

    (localDuplicateWarnings ++ predicateMappingsDuplicateWarnings ++ allMappingsDuplicateWarnings).toSeq
  }
}

ROBiolinkMappingsGenerator.main(args)
