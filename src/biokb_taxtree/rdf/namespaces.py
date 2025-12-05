"""RDF namespace URIs."""

from rdflib import Namespace

BASE_URI = "http://biokb.fraunhofer.de/taxtree/"

NCBI_TAXON_NS = Namespace("http://purl.obolibrary.org/obo/NCBITaxon_")

# BRENDA URIs to Fraunhofer
NODE_NS = Namespace(f"{BASE_URI}node#")
RELATION_NS = Namespace(f"{BASE_URI}relation#")
