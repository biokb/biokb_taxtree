### **BioKb Taxtree: A Python Library for Querying NCBI Taxonomy Data**  

**BioKb Taxtree** is a Python library designed to **load and query data from the NCBI Taxonomy database** in a structured and efficient manner. The library enables users to store taxonomy data in a database, allowing for **fast querying and advanced tree-based searches**.  

### **Flexible Database Management with SQLAlchemy**  
A key feature of **BioKb Taxtree** is its **database-agnostic design**, made possible by its integration with **SQLAlchemy**, a powerful Python SQL toolkit and Object-Relational Mapper (ORM). Because of this, the library supports multiple **Database Management Systems (DBMS)**, including:  

- **PostgreSQL**  
- **MySQL / MariaDB**  
- **SQLite**  
- **Microsoft SQL Server**  
- **Oracle Database**  

This flexibility allows researchers and developers to choose the database system that best fits their needs, whether for **local analysis** (e.g., SQLite) or **enterprise-scale applications** (e.g., PostgreSQL or Oracle).  

### **Querying Name Classes in NCBI Taxonomy**  
NCBI Taxonomy assigns multiple **name classes** to taxa, reflecting different ways a species or group can be identified. **BioKb Taxtree** allows users to query taxonomy data based on these name classes, including:  

- **scientific name** (officially recognized name)  
- **synonym** (alternative names)  
- **common name** (vernacular names)  
- **misspelling** (frequent misidentifications)  
- **authority** (taxonomic authorship details)  
- **equivalent name** (alternative valid names)  
- **in-part** (partial names)  
- **includes** (grouping broader than a single taxon)  
- **genbank common name** (name used in GenBank records)  
- **blast name** (name used in BLAST searches)  

### **Advanced Tree-Based Searching**  
The library provides several **functions for navigating the NCBI taxonomy tree**, enabling users to:  

✅ **Search for taxa by name or taxonomic ID**  
✅ **Retrieve parent or child nodes in the hierarchy**  
✅ **Find sibling taxa**  
✅ **Trace lineage from a taxon to the root**  
✅ **List all descendant taxa of a given node**  

Additionally, **BioKb Taxtree** supports **branch-specific searches**, meaning users can **limit queries to specific taxonomic subtrees**, such as all species within a given genus, family, or higher taxonomic rank.  

### **Conclusion**  
**BioKb Taxtree** is a powerful tool for researchers, bioinformaticians, and database managers working with NCBI taxonomy data. By supporting multiple **DBMS systems via SQLAlchemy** and offering **advanced tree-searching capabilities**, the library enables efficient and flexible taxonomy management for various applications in **genomics, systematics, and biodiversity research**.