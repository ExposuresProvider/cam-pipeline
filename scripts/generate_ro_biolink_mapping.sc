//> using scala "2.13"
//> using dep "dev.zio::zio:2.0.15"
//> using dep "dev.zio::zio-streams:2.0.15"
//> using dep "dev.zio::zio-json:0.6.0"
//> using dep "io.circe::circe-core:0.14.5"
//> using dep "io.circe::circe-generic:0.14.5"
//> using dep "io.circe::circe-parser:0.14.5"
//> using dep "io.circe::circe-yaml:0.14.2"
//> using dep "com.typesafe.scala-logging::scala-logging:3.9.5"
//> using dep "ch.qos.logback:logback-classic:1.4.8"

import scala.io._

import java.io._

import zio._
import zio.Console._
import zio.stream._
import zio.json._
import com.typesafe.scalalogging._
import io.circe._
import io.circe.generic.auto._

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
  /* Some manual annotations (we should try to move these into Biolink model so we don't need to deal with them ourselves. */

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
  case class Conf(
                   outputFilename: String,
                   biolinkVersion: String = "v3.5.2"
                 )

  /** Overall code for running this generator. */
  override def run = for {
    conf <- readCommandLineArgs
    _ = logger.info(s"Output filename: ${conf.outputFilename}")

    githubBiolinkModel <- getPredicateMappingsFromBiolinkModel(conf)
    githubPredicateMappings <- getPredicateMappingsFromGitHub(conf)
    _ = logger.info(s"Loaded ${githubBiolinkModel.length} mappings from the Biolink model and ${githubPredicateMappings.length} mappings from the predicate mappings file.")

    countPredsWritten <- writePredicates(githubBiolinkModel ++ githubPredicateMappings ++ manualPredicateMappingRows, conf.outputFilename)
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
    _ = outputFile.write("mapping_type\tpredicate\tbiolink_predicate\tobject_aspect_qualifier\tobject direction qualifier\tqualified_predicate\n")
  } yield {
    predicates.foreach(predicate => {
      def writePredicatesOfMappingType(mapping_type: String, predicate_id: String, predicateMappingRow: PredicateMappingRow) = {
        outputFile.write(
          s"${mapping_type}\t${predicate_id}\t${predicateMappingRow.predicate}\t${predicateMappingRow.`object aspect qualifier`.getOrElse("")}\t" +
            s"${predicateMappingRow.`object direction qualifier`.getOrElse("")}\t${predicateMappingRow.`qualified predicate`.getOrElse("")}\n")
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

  def releaseSource(source: => Source): ZIO[Any, Nothing, Unit] =
    ZIO.succeedBlocking(source.close())

  /** A ZIO wrapper for scala Sources. */
  def sourceForURL(url: => String): ZIO[Scope, IOException, Source] =
    ZIO.acquireRelease(acquireSourceByURL(url))(releaseSource(_))

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
                                )

  /** Since the predicate mappings file consists of a top level `predicate mappings` element, we need to
   * replicate that in order to be able to read it. */
  case class PredicateMappings(
                                `predicate mappings`: List[PredicateMappingRow]
                              )

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

          val mappings = exactMappings.map(m => ("exact", m)) ++
            closeMappings.map(m => ("close", m)) ++
            broadMappings.map(m => ("broad", m)) ++
            narrowMappings.map(m => ("narrow", m))

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

  /** To initialize this object, we need to download and parse the predicate_mapping.yaml file from the Biolink model, which needs to be
   * downloaded to the package resources (src/main/resources) from
   * https://github.com/biolink/biolink-model/blob/${biolinkVersion}/predicate_mapping.yaml (the raw version is available from
   * https://raw.githubusercontent.com/biolink/biolink-model/v3.2.1/predicate_mapping.yaml)
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


}

ROBiolinkMappingsGenerator.main(args)