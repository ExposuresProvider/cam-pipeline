import $ivy.`net.sourceforge.owlapi:owlapi-distribution:4.5.15`
import $ivy.`org.phenoscape::scowl:1.3.4`
import $ivy.`com.outr::scribe-slf4j:2.7.11`

import java.io.File

import org.phenoscape.scowl._
import org.semanticweb.owlapi.apibinding.OWLManager
import org.semanticweb.owlapi.formats.FunctionalSyntaxDocumentFormat
import org.semanticweb.owlapi.model.IRI

import scala.collection.JavaConverters._
import scala.io.Source

val source = Source.fromFile("uniprot-to-ncbi.txt", "utf-8")
  val rules = source.getLines().flatMap { line =>
    val columns = line.split("\t", -1)
    val uniprot = columns(0).trim
    val ncbis = columns(1).split(";", -1).map(_.trim).toSet
    val uniprotIRI = s"http://identifiers.org/uniprot/$uniprot"
    val ncbiIRIs = ncbis.map(id => s"http://identifiers.org/ncbigene:$id")
    ncbiIRIs.map { ncbiIRI =>
      Class(uniprotIRI)('x) --> Class(ncbiIRI)('x)
    }
  }
  val manager = OWLManager.createOWLOntologyManager()
  val ontology = manager.createOntology()
  manager.addAxioms(ontology, rules.toSet.asJava)
  manager.saveOntology(ontology, new FunctionalSyntaxDocumentFormat(), IRI.create(new File("uniprot-to-ncbi-rules.ofn")))
