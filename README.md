Description
Adds RefWorks as an export format to all Voyager OPAC pages, both single and multiple.

Based on work at Hamilton College, and updates by Ken Herold
Additional author(s):
Institution: Hamilton College
Year: 2009
License: BSD style
Short description: Use, modification and distribution of the code are permitted provided the copyright notice, list of conditions and disclaimer appear in all related material.
Skill required for using this code: Advanced.

Installation Instructions:

See PDF containing instructions in Download section--these are more of a recipe for advanced users than an exact guide.

Do NOT cut and paste code, particularly the embedded javascript--it is unforgiving of errors.

Depending on your local web serving, you may need to set your $report_dir to be exactly the DocumentRoot in

/m1/shared/apache2/conf/ConfiguredVirtualHosts/xxxdb_vwebv_httpd.conf

usually

/m1/voyager/xxxdb/tomcat/vwebv/context/vwebv/htdocs

When you change $report_dir, make sure your .tmp files are created where RefWorks expects the export.

WARNING: You MUST verify the $report_dir paths in doQuery and doQueryBulk to your local settings! Either hard-code or set to the commented lines:
open (OUTFILE, ">$report_dir/$out_file")

Take care to set the $out_file in refworks.ini so that the path makes sense when appended to the report dir.

HOSTED SITES: Your ORACLE_HOME may vary and your DBI connect strings must be customized.

SPLIT SERVER SITES: You will have to install the Oracle client yourself on your web server.
