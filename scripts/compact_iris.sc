//> using scala "2.13.14"
//> using dep "dev.zio::zio:2.0.15"
//> using dep "dev.zio::zio-streams:2.0.15"
//> using dep "dev.zio::zio-json:0.5.0"

import zio._
import zio.Console._
import zio.stream._
import zio.json._
import scala.io.Source
import java.io.File

object Script extends ZIOAppDefault {

    override def run = for {
        args <- getArgs
        prefixesFile <- ZIO.attempt(args(0))
        supplementalNamespacesFile <- ZIO.attempt(args(1))
        inFile <- ZIO.attempt(args(2))
        outFile <- ZIO.attempt(args(3))
        prefixes <- prefixesFromFile(prefixesFile)
        supplementalNamespaces <- prefixesFromFile(supplementalNamespacesFile)
        allNamespaces = prefixes.iterator.map(_.swap) ++ supplementalNamespaces
        namespaces = allNamespaces.toList.sortBy { case (ns, _) => -ns.size }
        stream <- ZStream.fromFileName(inFile)
            .via(ZPipeline.utf8Decode 
             >>> ZPipeline.splitLines 
             >>> ZPipeline.map(compactIRIs(_, namespaces))
             >>> ZPipeline.intersperse("\n") 
             >>> ZPipeline.utf8Encode)
            .run(ZSink.fromFileName(outFile))
    } yield ()

    def prefixesFromFile(filepath: String) = for {
        text <- ZIO.attempt(Source.fromFile(new File(filepath), "utf-8").mkString)
        prefixes <- ZIO.fromEither(text.fromJson[Map[String, String]])
    } yield prefixes

    def compactIRIs(line: String, namespaces: List[(String, String)]) = {
        val iriPattern = "^<(.+)>$".r
        line.split("\t", -1).map {
            case iriPattern(iri) => compactIRI(iri, namespaces)
            case other => other
        }.mkString("\t")
    }

    def compactIRI(iri: String, namespaces: List[(String, String)]) = 
        namespaces.find { case (ns, _) => iri.startsWith(ns) }
        .map { case (ns, prefix) => 
            val id = iri.substring(ns.size)
            s"$prefix:$id"
        }
        .getOrElse(iri)

}

Script.main(args)
