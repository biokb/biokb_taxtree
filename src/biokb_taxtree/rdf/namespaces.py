"""RDF namespace URIs."""

from rdflib import Namespace
from biokb_taxtree.constants.brenda import BASE_URI

tax_ns = Namespace("https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id=")

# BRENDA URIs to Fraunhofer
node = Namespace(f"{BASE_URI}/node#")
activation_ns = Namespace(f"{BASE_URI}/activation#")
inhibition_ns = Namespace(f"{BASE_URI}/inhibition#")
cofactor_ns = Namespace(f"{BASE_URI}/cofactor_interaction#")
ic50_ns = Namespace(f"{BASE_URI}/ic50#")
kcat_km_ns = Namespace(f"{BASE_URI}/kcat_km#")
ki_ns = Namespace(f"{BASE_URI}/ki#")
km_ns = Namespace(f"{BASE_URI}/km#")
relation = Namespace(f"{BASE_URI}/relation#")
location_ns = Namespace(f"{BASE_URI}/location#")
metal_ion_ns = Namespace(f"{BASE_URI}/metal_ion#")
nsp_reaction_ns = Namespace(f"{BASE_URI}/nsp_reaction#")
sp_reaction_ns = Namespace(f"{BASE_URI}/sp_reaction#")
information_ns = Namespace(f"{BASE_URI}/information#")

# BRENDA URIs to BRENDA
ec_ns = Namespace("https://www.brenda-enzymes.org/enzyme.php?ecno=")
reaction_ns = Namespace("https://www.brenda-enzymes.org/enzyme.php?reaction=")
compound_ns = Namespace("https://www.brenda-enzymes.org/ligand.php?brenda_ligand_id=")
