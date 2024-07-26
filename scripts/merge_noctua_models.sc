//> using scala "2.13.14"
//> using dep "dev.zio::zio:2.0.15"
//> using dep "dev.zio::zio-streams:2.0.15"
//> using dep "dev.zio::zio-json:0.5.0"
//> using dep "org.apache.jena:apache-jena-libs:4.8.0"

import zio._
import zio.Console._
import zio.stream._
import zio.json._
import scala.io.Source
import scala.jdk.CollectionConverters._
import java.io.File
import java.io.FileOutputStream
import java.nio.file.Path
import java.nio.file.Paths
import java.nio.file.Files
import java.util.stream.Collectors
import org.apache.jena.sparql.core.Quad
import org.apache.jena.vocabulary.OWL2
import org.apache.jena.vocabulary.RDF
import org.apache.jena.riot.system.StreamRDFWriter
import org.apache.jena.riot.RDFFormat
import org.apache.jena.riot.system.StreamRDF
import org.apache.jena.riot.RDFDataMgr
import org.apache.jena.rdf.model.ModelFactory
import org.apache.jena.rdf.model.Model
import org.apache.jena.rdf.model.Resource
import org.apache.jena.rdf.model.Property
import org.apache.jena.rdf.model.ResourceFactory

object Script extends ZIOAppDefault {

  val modelState = ResourceFactory.createProperty("http://geneontology.org/lego/modelstate")
  val providedBy = ResourceFactory.createProperty("http://purl.org/pav/providedBy")

  override def run = for {
    args <- getArgs
    modelsFolder <- ZIO.attempt(args(0))
    nQuadsOutput <- ZIO.attempt(args(1))
    nQuadsWriter <- createStreamRDF(nQuadsOutput)
    _ <- ZStream
      .fromIterableZIO(
        ZIO.attemptBlocking(
          Files.list(Paths.get(modelsFolder)).collect(Collectors.toList()).asScala
        )
      )
      .mapZIOParUnordered(8)(quads)
      .foreach(quads => ZIO.attemptBlocking(quads.foreach(nQuadsWriter.quad(_))))
  } yield ()

  def quads(path: Path): Task[Iterator[Quad]] = for {
    model <- ZIO.attemptBlocking(RDFDataMgr.loadModel(path.toFile().getPath()))
    modelIRI <- ZIO
      .fromOption(model.listResourcesWithProperty(RDF.`type`, OWL2.Ontology).asScala.toList.headOption)
      .orElseFail(new Exception(s"Model has no ontology IRI: $path"))
  } yield
    if (isProductionModel(model, modelIRI) || isReactomeModel(model, modelIRI))
      model.listStatements().asScala.map(_.asTriple()).map(Quad.create(modelIRI.asNode(), _))
    else Iterator.empty

  def isProductionModel(model: Model, modelIRI: Resource): Boolean = model
    .listObjectsOfProperty(modelIRI, modelState)
    .asScala
    .exists(n => n.isLiteral() && n.asLiteral().getLexicalForm() == "production")

  def isReactomeModel(model: Model, modelIRI: Resource): Boolean = model
    .listObjectsOfProperty(modelIRI, providedBy)
    .asScala
    .exists(n => n.isLiteral() && n.asLiteral().getLexicalForm() == "https://reactome.org")

  def createStreamRDF(path: String): ZIO[Scope, Throwable, StreamRDF] = 
    ZIO
      .acquireRelease(ZIO.attempt(new FileOutputStream(new File(path))))(stream => ZIO.succeed(stream.close()))
      .flatMap { outputStream =>
        ZIO.acquireRelease(ZIO.attempt {
          val stream = StreamRDFWriter
            .getWriterStream(outputStream, RDFFormat.NQUADS, null)
          stream.start()
          stream
        })(stream => ZIO.succeed(stream.finish()))
      }

}

Script.main(args)
