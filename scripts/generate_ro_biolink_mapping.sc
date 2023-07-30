//> using scala "2.13"
//> using dep "dev.zio::zio:2.0.15"
//> using dep "dev.zio::zio-streams:2.0.15"
//> using dep "dev.zio::zio-json:0.6.0"
//> using dep "com.typesafe.scala-logging::scala-logging:3.9.5"
//> using dep "ch.qos.logback:logback-classic:1.4.8"

import zio._
import zio.Console._
import zio.stream._
import zio.json._
import com.typesafe.scalalogging._

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
  case class Conf (
    outputFilename: String
                  )

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


  override def run = for {
    conf <- readCommandLineArgs
    _ = logger.info(s"Output filename: ${conf.outputFilename}")
  } yield ()

}

ROBiolinkMappingsGenerator.main(args)