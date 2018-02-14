// JavaScript Document
// In order to make users aware of session time out.
// Created by Jason Zou. 2005-09-21
// Modified by Jason Zou. 2007-02-08 (JQuery)
// Cleaned up the code.   2007-07-24
// Made it working with voyage 7 2009-04-24

if (typeof webvoyager == "undefined") {
  var webvoyager = new Object();
}

webvoyager.refworks={
  refworksURL : "http://.edu/vwebv/refworks.cgi",

  importBib:function(bib){
    var confirmed = confirm('Exporting this record to Refworks. Do you want to continue?');
    if (confirmed){
      this.sendBib(bib);
    }
  },

  sendBib:function(bib){
    if (bib) {
      myLink = this.refworksURL+bib;
      var w = window.open(myLink,"same","width=800,height=600,status=no,resizable=yes,scrollbars=yes");
 
}
  }
}
