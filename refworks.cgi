#!/m1/shared/bin/perl

use MIME::Base64;

########################################################################
#
#  refworks.cgi : Import a bib item or items into RefWorks
#
#  Version: 1.1 for Unix
#
#  Created by Qing Zou, qzou@lakeheadu.ca
#
#  Lakehead University 
#  955 Oliver, Thunder Bay, ON, Canada P7B5E1
#
#  This CGI/Perl script gets requests from webvoyage and 
#  extracts items from the Voyager database. Then it converts 
#  items into refworks file format and imports into refworks.
#  It can be incorporated into Webvoyager 6.1 or previous versions.
#
#  Some functions are derived from Michael Doran's newbooks cgi.
#
#  For more information, please contact me at qzou@lakeheadu.ca
#
#  Note: Ken Herold, Hamilton College 2014 for Linux RHEL 6.5
#  Substantially changed to process single and multiple records
#  added proxy variable to ini file and below  Ken 6/18/2009
#        also modified for call number Ken 6/19/2009
#       changed title_brief to title  Ken 8/11/2009 and back 8/31/2009
#      substantially modified to add MARC tags and trim fields Ken 8/26/2009
#
#  Additional changes for 1.0 by the github project maintainer
#
########################################################################
#
#  Copyright 2006-2008, Lakehead University.
#  All rights reserved.
#
########################################################################
#
#  "Voyager" and "WebVoyage" are trademarks of Endeavor Information
#  Systems, Inc. and/or successor entities
#
#  "RefWorks" is a trademark of ProQuest
#
########################################################################

#use strict;

#  This program requires the DBI and DBD::Oracle modules
#  which are not a part of the default Perl distribution.
#  Endeavor installs the database modules as part of the 
#  Voyager 2000.1 upgrade.

use DBI;

############################################################
#  Part 1 configuration: extracting the data
############################################################
#
#  Running as a crontab entry requires that we set some
#  environment variables that would already be set if we
#  were running this from the command line while logged in.
#  (To see if your values for these are the same, run the
#   "env" command while logged in as 'voyager' to your 
#   database server.)

$ENV{ORACLE_SID} = "VGER" unless exists( $ENV{ORACLE_SID} );

$ENV{ORACLE_HOME} = "/oracle/app/oracle/product/12.1.0.2/db_1" unless exists( $ENV{ORACLE_HOME} );

#  Database name
#  Substitute your database in place of traindb.

our $db_name = "traindb";

# URL PREFIX for proxy

our $proxy = '';

# This is the base url to use with the LK tag.
our $link_server;
# $link_server  =  "http://my.host/vwebv/holdingsInfo?bibId=" ;

#  Voyager (Oracle) read-only username and password

our $username = "ro_traindb";
our $password = "ro_traindb";

our %rtType = ("aa", "Book, Section", "ab", "Book, Section",
              "ai", "Book, Section", "am", "Book, Whole", "as", "Journal",
              "cm", "Music Score", "em", "Map", "gm", "Video/DVD",
              "im", "Sound Recording", "mm", "Computer Program", 
               "ms", "Computer Program");


require "./refworks.ini";


#  Parse form data 
our %formdata;
ReadParse();


##########################################################
#  Assign form data to variables.
##########################################################
#
# Handle both the canonical and broken PCOM methods of deliniating multiple IDs
my %bibList;
foreach my $key (keys %formdata ) {
   next unless $key =~ /^bibId\d*$/;
   $bibList{$formdata{$key}} = 1;
}
foreach my $v (ref $formdata{"id"} ? (@{$formdata{'id'}}) : $formdata{'id'} ) {
   $bibList{$v} = 1;
}

my $ok = 1;
my @bibList;
foreach my $id ( sort keys %bibList ) {
  if ( $id =~ /^\d+$/g ) {
     push @bibList, $id;
  } elsif ($id = /\S/ ) {
     print STDERR "INVALID ID '$id'\n";
     $ok = 0;
  }
}

if (!@bibList &&  exists($ENV{'PATH_INFO'})) {
  my $p = $ENV{'PATH_INFO'};
  $p =~ s/^\///;

  my $p_decoded = decode_base64($p);
  
  foreach my $id (split /\,/, $p_decoded) {
    if ( $id =~ /^\d+$/g ) {
      push @bibList, $id;
      } else {
       print STDERR "INVALID ID '$id'\n";
       $ok = 0;
    }
  }
  print STDERR "REFWORKS IN: $p '$p_decoded'\n" unless $ok == 1;
  print STDERR "REFWORKS INFO: ok=$ok IDS @bibList\n" unless $ok == 1;
}
    

if ($ok != 1 ) {
   print "Content-type: text/html\n\n";
   print "Invalid Arguments to script";
   exit 1;
}
    
if (@bibList && ! exists($ENV{'PATH_INFO'})) {
   my $new_uri = $ENV{'SCRIPT_URI'}."/".encode_base64(join(',', @bibList));
   #print STDERR "REFWORKS TARGET URI: $new_uri BIBLIST: ".join(',', @bibList)."\n";
  
   print "Location: $proxy$refworks_server?g=$refwork_id&vendor=Refworks%20Tagged%20Format&url=".${new_uri}."\n\n";
   exit 0;
}

print "Content-type: text/plain\n\n";

eval {
  DoQueryBulk($db_name, \@bibList);
}; 
if ($@) {
  print STDERR $@."\n";
  print "\n\nERROR: we were unable to process your request\n";
  exit 1;
}

exit 0;


##########################################################
#  Bulk import, this function imports more than one 
#  item into Refwork
##########################################################
sub ConstructSQLBulk{
    my ($db_name, $bibList) = @_;
    #  The SQL option "choice" is an artifact of previous
    #  versions.  This SQL query's embedded logic as to
    #  "what constitutes a new item" should be adequate
    #  for all sites.  If it isn't, you may create your
    #  own; however, it must output the same fields in
    #  order for the newbooks.cgi to utilize it.  -mdd

    my $ct = @$bibList - 1;
    $ct = 0 if $ct < 0;

    return "select distinct author, title_brief, edition, publisher, pub_place, pub_dates_combined, bib_format, isbn, issn, language, bib_text.bib_id,
        mfhd_master.display_call_no, mfhd_master.location_id
	from $db_name.bib_text, $db_name.bib_mfhd, $db_name.mfhd_master
        where
               bib_text.bib_id = bib_mfhd.bib_id and
               bib_mfhd.mfhd_id = mfhd_master.mfhd_id and
               bib_text.bib_id in (".( "?, " x $ct)." ? ) 
        order by bib_text.bib_id, mfhd_master.location_id";
     
}
##########################################################
#  Get possible Author information
##########################################################
sub getAuthorSQL{
    return "select display_heading
	from $db_name.bib_index
	where (index_code like '700_' or index_code like '710_') and bib_id = ? ";
}

##########################################################
#  Get possible Subject information
##########################################################
sub getSubjectSQL{
    return "select display_heading
       from
         $db_name.bib_index
       where
          (index_code like '650_' or index_code like '651_') and bib_id = ?";
}

##########################################################
#  Get possible MARC information
##########################################################
sub getMARCSQL {
   return "select bib_id, record_segment, seqnum
        from $db_name.bib_data
        where bib_id = ?  order by bib_id asc, seqnum desc";
}
	
##########################################################
#  After parsing, this function gets the ball rolling. 
##########################################################

sub DoQueryBulk {
    my ($db_name, $bibList) = @_;

    # Connect to Oracle database
    my $dbh = DBI->connect('dbi:Oracle:host=localhost;SID=VGER;port=1521', $username, $password)
	|| die "Could not connect: $DBI::errstr";

    my $q_str = ConstructSQLBulk($db_name, $bibList);
    my $sth = $dbh->prepare($q_str) 
	|| die $dbh->errstr;

    my $a_str = getAuthorSQL(); 
    my $authors = $dbh->prepare($a_str) 
	|| die $dbh->errstr;

    my $s_str = getSubjectSQL();
    my $subjects = $dbh->prepare($s_str) || die $dbh->errstr();

    my $m_str = getMARCSQL();
    my $marcs = $dbh->prepare($m_str) || die $dbh->errstr();

    $sth->execute(@$bibList) 
	|| die $dbh->errstr;


    my $old_id = "";
    while( my (@entry) = $sth->fetchrow_array() ) {
        my ($author, $title, $edition, $publisher, $place, $year, $rt_code,  $sn, $sn1, $lang, $id, $display_call_no, $location_id) = (@entry);

        #Limit to one entry per bib_id if there are multiple locations 
        next if $old_id eq $id;
        $old_id = $id;

        my @tags;

        if ($rt_code) {
           push @tags, "RT ".(exists($rtType{$rt_code}) ? $rtType{$rt_code} : 'Generic'); 
        }

        push @tags, "A1 $author" if $author;

        $authors->execute($id) || die $dbh->errstr();

        while (my (@authorEntry) = $authors->fetchrow_array() ) {
          if ($author) {
             push @tags, "A2 ".$authorEntry[0];
          } else {
             $author = $authorEntry[0];
             push @tags, "A1 ".$authorEntry[0];
          }
        }
        $authors->finish();

        push @tags, "T1 $title" if $title;

        push @tags, "ED $edition" if $edition;

        if ($publisher) {
           $publisher =~ s/\s*,\s*$//; 
           push @tags, "PB $publisher";
        }

        if ($place) {
           $place =~ s/:|\[|]|,\*+$//g;
           push @tags, "PP $place";
        }

        push @tags, "YR $year" if $year;

        push @tags, "SN $sn" if $sn;

        push @tags, "SN $sn1" if $sn1;

        push @tags, "LA $lang" if $lang;

        push @tags, "CN $display_call_no" if $display_call_no;

        push @tags, "U1 $location_id" if $location_id;

        my @marcdata = GetMARCData($marcs, $id);

        push @tags, (@marcdata) if @marcdata;

        $subjects->execute($id) ||
           die $dbh->errstr;

        while( my (@subjectEntry) = $subjects->fetchrow_array() ) {
           push @tags, "K1 ".$subjectEntry[0] if $subjectEntry[0];
        }

        push @tags, "LK  ".${link_server}.$id if ($id && defined ${link_server});

        print join("\n", @tags)."\n\n";
    }
     
    $sth->finish;

    $dbh->disconnect;
}

sub GetMARCData {
  my ($sth, $id) = @_;
  my @tags;
  
  $sth->execute($id) || die $dbh->errstr();

  my $marcstuff = "";
  my $marc = "";
  my $oldrec_id = 0;
  while (my (@r) = $sth->fetchrow_array) {
    my ($rec_id, $recseg, $seqnum) = (@r);  
    if ($rec_id != $oldrec_id) {
      $marcstuff .= $marc;
      $oldrec_id = $rec_id;
      $marc = $recseg;
    } else {
      $marc = $recseg . $marc;
    }
  }
  $marcstuff .=  $marc;

  my ($ab, $sp, $n0, $n4, $n5, $n9, $ul) = ('', '', '', '','', '', '');

  foreach my $marcrec (split /\x1d/, $marcstuff ) {
    my $leader  = substr($marcrec, 0, 24);
    my $reclen  = substr($marcrec, 1, 5);
    my $baseaddr = substr($marcrec, 12, 5) - 1;
    my $strptr = 24;

    while ($strptr < $baseaddr-1) {
      my $tagid   = substr($marcrec, $strptr, 3);
      my $taglen  = substr($marcrec, $strptr+3, 4);
      my $offset  = substr($marcrec, $strptr+7, 5);
      my $tagdata = substr($marcrec, $baseaddr+$offset, $taglen);

      $tagdata =~ s/\x1f[a-z]/ \|$& /g;
      $tagdata =~ s/\x1f//g;
      $tagdata =~ s/\x1e//g;

      $tagdata = substr($tagdata, 0, 2) . substr($tagdata, 3) if (substr($tagdata, 2, 2) eq " |") ;

      $tagdata =~ s/\|[a-z]//g;

      if ($tagid == "520") {$ab = $tagdata;}
      if ($tagid == "300") {$sp = $tagdata;}
      if ($tagid == "500") {$n0 = $tagdata." ".$n0;}
      if ($tagid == "504") {$n4 = $tagdata;}
      if ($tagid == "510") {$n5 = $tagdata; $n5 =~ s/^4//g;}
      if ($tagid == "590") {$n9 = $tagdata;}
      if ($tagid == "856") {$ul = $tagdata; $ul =~ s/^.{3}//g;}
      #    printf("%3s:%4s:%5s:%s\n", $tagid, $taglen, $offset, $tagdata);
      $strptr+= 12;
    }
  }

  my $n = $n0.$n4.$n5.$n9;

  push @tags, "UL ".$ul if $ul;
  push @tags, "NO ".$n  if $n;
  push @tags, "AB ".$ab if $ab;
  push @tags, "SP ".$sp if $sp;
  return @tags;

}


##########################################################
#  ReadParse
##########################################################
#
#  ReadParse reads in and parses the CGI input.
#  It reads  / QUERY_STRING ("get"  method)
#            \    STDIN     ("post" method)

sub ReadParse {
	%formdata=();

    my $myformdata; 
    # Retrieve useful ENVIRONMENT VARIABLES
    my $method = $ENV{'REQUEST_METHOD'};

    # If method unspecified or if method is GET
    if ($method eq  '' || $method eq 'GET') {
        # Read in query string
        $myformdata = $ENV{'QUERY_STRING'};
    }
    # If method is POST
    elsif ($method eq 'POST') {
        read(STDIN, $myformdata, $ENV{'CONTENT_LENGTH'});
    }
    else {
        die "Unknown request method: $method\n";
    }

    foreach my $pair ( split(/&/, $myformdata) ) {
        # names and values are split apart
        my ($name, $value) = split(/=/, $pair , 2);
        # pluses (+'s) are translated into spaces
        $value =~ tr/+/ /;
        # hex values (%xx) are converted to alphanumeric
        $name  =~ s/%([a-fA-F0-9][a-fA-F0-9])/pack("C", hex($1))/eg;
        $value =~ s/%([a-fA-F0-9][a-fA-F0-9])/pack("C", hex($1))/eg;
        # The code below attempts to ferret out shell meta-characters
        # in the form input.  It replaces them with spaces.
        # looking for the presence of shell meta-characters in $name
        $name  =~ s/[{}\!\$;><&\*'\|]/ /g;
        # looking for the presence of shell meta-characters in $value
        $value =~ s/[{}\!\$;><&\*'\|]/ /g;

        $name = lc($name);

        if (! exists $formdata{$name} ) {
          $formdata{$name} = $value;
        } elsif (ref($formdata{$name}) eq 'ARRAY') {
          push @{$formdata{$name}}, $value;
        } else {
          $formdata{$name} = [ $formdata{$name} , $value ];
        }
    }
}
