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

/* Data structures */

/** A labeled IRI consists of an IRI and an optional number of labels. */
case class LabeledIRI(
                       iri: String,
                       label: Set[String]
                     )

/** A single TRAPI qualifier. */
final case class TRAPIQualifier(qualifier_type_id: String, qualifier_value: String)

/** A TRAPI qualifier constraint consists of a list of TRAPI Qualifiers */
final case class TRAPIQualifierConstraint(qualifier_set: List[TRAPIQualifier])

/**
 * A PredicateMapping defines a mapping from a "predicate", a Relation Ontology (RO) term to a
 * "qualified Biolink Predicate", which consists of a Biolink Predicate and a Biolink Qualifier Constraint.
 * The goal is for this mapping to be reversible: we can replace the RO term with the qualified Biolink predicate,
 * or replace the qualified Biolink predicate with the RO term.
 *
 * TODO: rename biolinkQualifiers to biolinkQualifiedConstraint to make it clearly that it isn't a list of constraints.
 */
case class PredicateMapping(
                             predicate: LabeledIRI,
                             biolinkPredicate: Option[LabeledIRI],
                             biolinkQualifiers: Option[TRAPIQualifierConstraint]
                           )

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
  /* Configuration for this generator */
  case class Conf(
                   outputFilename: String,
                   biolinkVersion: String = "v3.5.2"
                 )

  override def run = for {
    conf <- readCommandLineArgs
    githubPredicateMappings <- getPredicateMappingsFromGitHub(conf)

    _ = logger.info(s"Output filename: ${conf.outputFilename}")
    _ = logger.info(s"GitHub predicate mappings: ${githubPredicateMappings}")
  } yield ()

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


  /** A case class for predicate mappings. */
  case class PredicateMappingRow(
                                  `mapped predicate`: String,
                                  `object aspect qualifier`: Option[String],
                                  `object direction qualifier`: Option[String],
                                  predicate: String,
                                  `qualified predicate`: Option[String],
                                  `exact matches`: Option[Set[String]]
                                ) {

    def qualifiers: Seq[TRAPIQualifier] = (`object aspect qualifier` match {
      case Some(aspect: String) =>
        List(TRAPIQualifier(qualifier_type_id = "biolink:object_aspect_qualifier", qualifier_value = aspect.replace(' ', '_')))
      case _ => List()
    }) ++ (`object direction qualifier` match {
      case Some(direction: String) =>
        List(TRAPIQualifier(qualifier_type_id = "biolink:object_direction_qualifier", qualifier_value = direction.replace(' ', '_')))
      case _ => List()
    }) ++ (`qualified predicate` match {
      case Some(qualified_predicate: String) =>
        List(
          TRAPIQualifier(qualifier_type_id = "biolink:qualified_predicate",
            qualifier_value = qualified_predicate.replace(' ', '_')
          ))
      case _ => List()
    })

    def qualifierConstraint: TRAPIQualifierConstraint = TRAPIQualifierConstraint(qualifier_set = qualifiers.toList)

    def qualifierConstraintList = List(qualifierConstraint)
  }

  case class PredicateMappings(
                                `predicate mappings`: List[PredicateMappingRow]
                              )

  def getPredicateMappingsFromBiolinkModel(conf: Conf): RIO[Any, List[PredicateMappingRow]] =
    for {
      biolinkModelText <- ZIO.attempt {
        Source
          .fromURL(s"https://raw.githubusercontent.com/biolink/biolink-model/${conf.biolinkVersion}/biolink_model.yaml")
          .getLines()
          .mkString("\n")
      }
      biolinkModelYaml <- ZIO.fromEither(io.circe.yaml.parser.parse(biolinkModelText))
      biolinkModelCursor = biolinkModelYaml.hcursor
      slotsCursor = biolinkModelCursor.downField("slots")
      slots <- ZIO.fromOption(slotsCursor.keys)
      roMapping <- ZStream.fromIterable(slots)
        .flatMap(slot => {
          val slotCursor = slotsCursor.downField(slot)

          for {
            exactMappings <- ZIO.fromEither(slotCursor.downField("exact_mappings").as[List[String]])
            closeMappings <- ZIO.fromEither(slotCursor.downField("close_mappings").as[List[String]])
            broadMappings <- ZIO.fromEither(slotCursor.downField("broad_mappings").as[List[String]])
            narrowMappings <- ZIO.fromEither(slotCursor.downField("narrow_mappings").as[List[String]])
            mappings = exactMappings.map(m => ("exact", m)) ++
              closeMappings.map(m => ("close", m)) ++
              broadMappings.map(m => ("broad", m)) ++
              narrowMappings.map(m => ("narrow", m))
            roMappings = mappings
              .filter({ case (_, mapp) => mapp.startsWith("RO:") })
              .map({ case (mtype, mapp) => (mtype, "http://purl.obolibrary.org/obo/RO_" + mapp.substring(2)) })
          } yield {
            ZStream.fromIterable(roMappings).map(roMapping =>
              PredicateMappingRow(
                `mapped predicate` = "biolink:" + slot.replace(' ', '_'),
                `object aspect qualifier` = None,
                `object direction qualifier` = None,
                predicate = roMapping._2,
                `qualified predicate` = None,
                `exact matches` = None
              )
            )
          }
        })
    } yield roMapping

  /** To initialize this object, we need to download and parse the predicate_mapping.yaml file from the Biolink model, which needs to be
   * downloaded to the package resources (src/main/resources) from
   * https://github.com/biolink/biolink-model/blob/${biolinkVersion}/predicate_mapping.yaml (the raw version is available from
   * https://raw.githubusercontent.com/biolink/biolink-model/v3.2.1/predicate_mapping.yaml)
   */
  def getPredicateMappingsFromGitHub(conf: Conf): RIO[Any, List[PredicateMappingRow]] =
    for {
      predicateMappingText <- ZIO.attempt {
        Source
          .fromURL(s"https://raw.githubusercontent.com/biolink/biolink-model/${conf.biolinkVersion}/predicate_mapping.yaml")
          .getLines()
          .mkString("\n")
      }
      predicateMappingsYaml <- ZIO.fromEither(io.circe.yaml.parser.parse(predicateMappingText))
      predicateMappings <- ZIO.fromEither(predicateMappingsYaml.as[PredicateMappings])
    } yield predicateMappings.`predicate mappings`

  /** Compares two qualifier lists. */
  def compareQualifierConstraints(ql1: List[TRAPIQualifier], ql2: List[TRAPIQualifier]): Boolean = {

    val set1 = ql1.map(q => (q.qualifier_value, q.qualifier_type_id)).toSet
    val set2 = ql2.map(q => (q.qualifier_value, q.qualifier_type_id)).toSet

    (set1 == set2)
  }

  /** Convert predicate data into a list of QualifiedBiolinkPredicates in case anyone wants a list of all the predicates we understand.
   */
    /*
  val qualifiedPredicatesData: Seq[QualifiedBiolinkPredicate] = predicatesData
    .flatMap {
      case PredicateMapping(_, Some(biolinkPredicate), None) => Some(QualifiedBiolinkPredicate(biolinkPredicate))
      case PredicateMapping(_, Some(biolinkPredicate), Some(TRAPIQualifierConstraint(qualifierList))) =>
        Some(QualifiedBiolinkPredicate(biolinkPredicate, qualifierList))
      case _ => None
    }*/
}

ROBiolinkMappingsGenerator.main(args)