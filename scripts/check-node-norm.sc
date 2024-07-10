//> using scala "2.13"
//> using dep "dev.zio::zio:2.1.5"
//> using dep "dev.zio::zio-streams:2.1.5"

import zio._
import zio.stream._

/**
 * This script checks whether all of the nodes produced by our script can be
 * normalized using NodeNorm.
 *
 * It should be called with a single command-line argument: the kg.tsv file to
 * be checked.
 */

object CheckNodeNorm extends ZIOAppDefault {

    case class KGEntry(
                      subj: String,
                      pred: String,
                      obj: String,
                      modelURL: String,
                      source: String
                      )

    object KGEntry {
        def fromTSVLine(line: String): KGEntry = {
            val cols = line.split('\t')
            KGEntry(
                cols(0),
                cols(1),
                cols(2),
                cols(3),
                cols(4)
            )
        }
    }

    override def run = for {
        args <- getArgs
        kgTsvFilename <- ZIO.attempt(args(0))
        outputFilename <- ZIO.attempt(args(1))
        _ = println(s"Reading knowledge graph from ${kgTsvFilename} and writing it to ${outputFilename}")
        _ <- ZStream.fromFileName(kgTsvFilename)
          .via(ZPipeline.utf8Decode >>> ZPipeline.splitLines)
          .map(KGEntry.fromTSVLine)
          .groupByKey(_.modelURL) {
              (modelURL, entries) => ZStream.fromZIO(for {
                  nodes <- (entries.map(_.subj) ++ entries.map(_.obj)).runCollect
                  line = s"${modelURL}\t${nodes.toSet.toSeq.sorted.mkString("||")}"
              } yield line)
          }
          .via(ZPipeline.intersperse("\n") >>> ZPipeline.utf8Encode)
            .run(ZSink.fromFileName(outputFilename))
    } yield ()

}

CheckNodeNorm.main(args)
