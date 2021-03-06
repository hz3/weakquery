#!/usr/bin/perl -w

# -----------------------------------------------------------------
# Name:      rerankrt24merge.pl
# Author:    Kiduk Yang, 07/23/2007
#              modified, 06/05/2007
#              combined trec07/blog/rerankrt24merge.pl and rerankrt24mergenew.pl
#              $Id: rerankrt24merge.pl,v 1.5 2008/04/23 04:21:46 kiyang Exp $
# -----------------------------------------------------------------
# Description:  consolidate rankset results from rerankrt13pnew.pl
#    foreach result file
#      1. print warning to LOG for missing files
#      2. merge rank subset reranking files generated by rerankrt13pnew.pl
#      3. merge w/ original result to get 1000 records per QN
#      4. output merged file
# -----------------------------------------------------------------
# ARGUMENT: 
#   arg1= query type (t, tx, e, ex)
#   arg2= result subdirectory (e.g. s0)
#   arg3= number of rsets per result (optional: default=10)
#   arg4= rset suffix (3 for rset3)
# INPUT:     
#   $ddir/results(_new)/$qtype/trecfmt(x)/$arg3/$runname
#     -- original TREC format results
#        QN 0 docID RANK RT_SC RunName (per line)
#   $ddir/results/$qtype/trecfmt(x)/$arg3.R/rset3/$runname-N.1
#     -- results w/ topic reranking scores
#        QN docID RANK RT_SC RunName Topic_SCs (per line)
#   $ddir/results/$qtype/trecfmt(x)/$arg3.R/rset3/$runname-N.2
#     -- results w/ opinion reranking scores
#        QN docID RANK RT_SC RunName Opinion_SCs (per line)
# OUTPUT:    
#   $ddir/results/$qtype/trecfmt(x)/$arg3.R/rall3/$runname.1
#   $ddir/results/$qtype/trecfmt(x)/$arg3.R/rall3/$runname.2
#   $ddir/rrlog/$prog      -- program     (optional)
#   $ddir/rrlog/$prog.log  -- program log (optional)
# -----------------------------------------------------------------
# NOTES: 
#   1. works the same as rerankrt13new.pl except it process a rank subset of results
#   2. rank set size is set to 100 (process 100 ranks per run)
# ------------------------------------------------------------------------

use strict;
use Data::Dumper;
$Data::Dumper::Purity=1;

my ($debug,$filemode,$filemode2,$dirmode,$dirmode2,$author,$group);
my ($log,$logd,$sfx,$noargp,$append,@start_time);

$log=1;                              # program log flag
$debug=0;                            # debug flag
$filemode= 0640;                     # to use w/ perl chmod
$filemode2= 640;                     # to use w/ system chmod
$dirmode= 0750;                      # to use w/ perl mkdir
$dirmode2= 750;                      # to use w/ system chmod (directory)
$group= "trec";                      # group ownership of files
$author= "kiyang\@indiana.edu";      # author's email


#------------------------
# global variables
#------------------------

my $wpdir=  "/u0/widit/prog";           # widit program directory
my $tpdir=  "$wpdir/trec08";            # TREC program directory
my $pdir=   "$tpdir/blog";              # TREC program directory
my $ddir=   "/u3/trec/blog08";          # index directory
my $qdir=   "$ddir/query";              # query directory
my $logdir= "$ddir/rrlog";              # log directory

# query type
my %qtype= (
"t"=>"results/train/trecfmt",
"tx"=>"results/train/trecfmtx",
"t2"=>"results/train2/trecfmt",
"tx2"=>"results/train2/trecfmtx",
"e"=>"results/test/trecfmt",
"ex"=>"results/test/trecfmtx",
"e2"=>"results/test2/trecfmt",
"ex2"=>"results/test2/trecfmtx",
);

require "$wpdir/logsub2.pl";    # subroutine library
require "$pdir/blogsub.pl";     # blog subroutine library


#------------------------
# program arguments
#------------------------
my $prompt=
"arg1= query type (t, tx, e, ex)\n".
"arg2= result subdirectory (e.g. s0)\n".
"arg3= number of rsets per result (optional: default=10)\n".
"arg4= rset suffix (optional: e.g. 4 for rset4)\n";

my %valid_args= (
0 => " t tx e ex t2 tx2 e2 ex2 ",
1 => " s0* ",
);

my ($arg_err,$qtype,$rsubd,$maxrn2,$rsetnum)= chkargs($prompt,\%valid_args,2);
die "$arg_err\n" if ($arg_err);

my $maxrn= 10;   # number of rset files per result
$maxrn=$maxrn2 if ($maxrn2);

# determine directory names
my $docdname;
if ($qtype=~/x/) { 
    $docdname= "docx"; 
}
else { 
    $docdname= "docs"; 
}

# TREC format directory
#   e.g., /u3/trec/blog07/results_new/trecfmtx
my $rdir= "$ddir/$qtype{$qtype}";      

my $ind0= "$rdir/$rsubd";             # original result directory
my $ind=  "$rdir/$rsubd"."R/rset$rsetnum";    # input directory
my $outd= "$rdir/$rsubd"."R/rall$rsetnum";    # output directory

`mkdir $outd` if (!-e "$outd");


#-------------------------------------------------
# start program log
#-------------------------------------------------

$sfx= "$qtype$rsubd";         # program log file suffix
$sfx .= $rsetnum if ($rsetnum);
$noargp=0;              # if 1, do not print arguments to log
$append=0;              # log append flag

# logs for different runs are appended to the same log file
if ($log) {
    @start_time= &begin_log($logdir,$filemode,$sfx,$noargp,$append);
    print LOG "InF   = $ind/*-(1..10).1, *-(1..10).2\n",
              "        $ind0/*\n",
              "OutF  = $outd/*.1, *.2\n\n";
}


#-------------------------------------------------
# 1. read in rset files
# 2. ouput merged files
#-------------------------------------------------

opendir(IND,$ind) || die "can't opendir $ind";
my @files=readdir(IND);
closedir IND;

my %runs;
foreach my $file(@files) {
    next if ($file !~ /^(.+?)\-\d{1,2}\.[12]$/);
    $runs{$1}++;
}

# check for mising rset files
RUN: foreach my $run(keys %runs) {
    my $origf= "$ind0/$run";
    foreach my $fext(1,2) {
        my %result;
        for(my $i=1; $i<=$maxrn; $i++) {
            my $inf="$ind/$run-$i.$fext";
            if (!-e $inf) {
                # print warning if missing
                print LOG "  !!Warning!!: missing $inf\n";
                next;
                #next RUN;
            }
            print LOG "Reading $inf\n";
            &mergeRset($inf,\%result);
        }
        # output merged file
        #  - pad the results to 1000 per QN if needed
        my $run2=$run;
        $run2=~s/_trec//;
        my $outf= "$outd/$run2.$fext";
        &output($origf,$outf,\%result);
    }
}
    

#-------------------------------------------------
# end program
#-------------------------------------------------

&end_log($pdir,$logdir,$filemode,@start_time) if ($log);

# notify author of program completion
#&notify($sfx,$author);


#####################
# subroutines
#####################

BEGIN { print STDOUT "\n"; }
END { print STDOUT "\n"; }

#-----------------------------------------------------------
# merge rset files into %result
#-----------------------------------------------------------
# arg1 = reset file
# arg2 = pointer to %result
#          key (QN -> rank) = val (result line)
#-----------------------------------------------------------
sub mergeRset {
    my($in,$rhp)=@_;
    my $debug=0;

    open(IN,$in) || die "can't read $in";
    while(<IN>) {
        my($qn,$dn,$rank)=split/\s+/;
        $rhp->{$qn}{$rank}=$_;
    }
    close IN;

} #endsub mergeRset


#-----------------------------------------------------------
# output hash to file
#-----------------------------------------------------------
# arg1 = original result file
# arg2 = output file
# arg2 = pointer to %result
#          key (QN -> rank) = val (result line)
#-----------------------------------------------------------
sub output {
    my($in,$out,$rhp)=@_;
    my $debug=0;

    open(IN,"$in") || die "can't read $in";
    my %rt;
    my ($oldqn,$rank)=(0);
    while(<IN>) {
        chomp;
        my ($qn,$c,$docID,$rnk,$sc,$run)=split/\s+/;
        $rank=0 if ($oldqn ne $qn);
        $rank++;
        $rt{$qn}{$rank}="$qn $docID $rank $sc $run";
        $oldqn=$qn;
    }
    close IN;

    print LOG "  Merged: writing to $out\n";
    open(OUT,">$out") || die "can't write to $out";

    foreach my$qn(sort {$a<=>$b} keys %{$rhp}) {
        for (my $rank=1;$rank<=1000;$rank++) {
        #foreach my$rank(sort {$a<=>$b} keys %{$rhp->{$qn}}) {
            if ($rhp->{$qn}{$rank}) {
                print OUT $rhp->{$qn}{$rank};
            }
            elsif ($rt{$qn}{$rank}) {
                print OUT "$rt{$qn}{$rank}\n";
            }
            else {
                print LOG "  Warning!! Only $rank results in QN=$qn\n";
                last;
            }
        }
    }
    close OUT;
    print LOG "\n";

} #endsub output


