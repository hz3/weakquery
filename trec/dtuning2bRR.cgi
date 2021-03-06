#!/usr/bin/perl

# -----------------------------------------------------------------
# Name:      dtuning2bRR.cgi
# Author:    Kiduk Yang, 4/22/08
#              modified dtuning2b.cgi (7/07)
#              modified dtuning2b_qe.cgi, 7/2/2008
# -----------------------------------------------------------------
# Description:
#   display blog topics or results list
#    - to handle idist and wqx phrase scores
# -----------------------------------------------------------------          
# NOTE:     !! must run dtuning1RR.pl after rerank file have been updated !!
# ------------------------------------------------------------------------

use CGI qw(:standard -debug);
use CGI::Carp (fatalsToBrowser);


#------------------------
# global variables
#------------------------

$maxrank=500;
$maxrank3=100;

%ids = ();

# 4: Rel -Op, 3: Rel +Op, 2: Rel Op, 1: Rel, Non-op, 0: Irrel, -1: Not judged 
%score_cl=(
-1=>'<font color="#000000" size="-1">', 
0=>'<font color="#8B2323" size="+2">', 
1=>'<font color="#FF6EC7" size="+1">', 
2=>'<font color="#32CD32">', 
3=>'<font color="#32CD32">', 
4=>'<font color="#32CD32">'
);

#total number of relevant doc in TREC assessment
$topicrel = 0; 
$opinonrel = 0;

#total number of retrieved relevant doc 
$topicrel_ret = 0; 
$opinonrel_ret = 0;

$tooltip= '<div id="balloonNUM" class="balloonstyle" style="width: 350px; background-color: lightyellow">TIP</div>';

# opNames w/o polarity & singleWTs:
my @vname1=('in1','in2','av','avx','em','emx','emd');

# opNames w/ polarity & multiWTs: idist2 scores not utilized
my @vname3=('ac','hf','iu','lf','w1','w2','acx','acd','hfx','hfd','iux','iud','lfx','lfd','w1x','w1d','w2x','w2d');

my @vnameOP=@vname1;

foreach my $name(@vname3) {
    foreach my $pol('','P','N') {
        push(@vnameOP,$name.$pol);
    }
}


#@vnameOP=('in1','in2','em','emx','emd','ac','hf','iu','lf','w1','w2','acx','acd','hfx','hfd','iux','iud','lfx','lfd','w1x','w1d','w2x','w2d');
#@vnameOP=('in1','in2','em','emx','emd','ac','hf','iu','lf','w1','w2','acx','hfx','iux','lfx','w1x','w2x','acd','hfd','iud','lfd','w1d','w2d');

@vnameT=('ex1','ex2','px1','px2','px3','ph','ph2','nr','nr2');

# opinion score order in result file
#  - reordered for display
my @vname2=('in1','in2','ac','acx','acd','iu','iux','iud','lf','lfx','lfd','hf','hfx','hfd','w1','w1x','w1d','w2','w2x','w2d','em','emx','emd','av','avx');


#-------------------------------------------------
# process form input from the mail entry page
#-------------------------------------------------
$rdir = "/u3/trec/blog08/results"; #results directory
$tdir = "/u1/trec/topics";        #topic directory  
$qdir = "/u3/trec/blog08/query";  #query directory

# get the parameter values from the form
$rsubd=param("rsubd");
$rfile=param("rfile"); #results file e.g. train/trecfmtx/s0qxfR1/okapi-bestfF.r2
$qnumber=param("qn");
$qtype=param("qt"); #query type
$dtype=param("dsptype"); #display type
$useolp=param("useolp"); #display type
$relonly=param("relonly"); 
$relonly0=param("relonly0"); 
$wtgrp=param("wtgrp");   # group cutoff to apply the second set of fusion weights
#$fsnum=param('fsnum');   # number of fusion component

$maxrank2=param("maxrank2");
$maxrank=$maxrank2 if ($maxrank2);
#$maxrank=900; ##!!

$submit=param("submit");

$cgi="dtuning2bRR.cgi";

#rerank directory
$rrdir="$rdir/$rfile";
$rrdir=~s|($rsubd)|rerank/$1|;
$rrdir=~m|^(.+/rerank)|;
$rrlogf="$1/rerank.log";          # rerank saved log

$rrdir_new="$rrdir/new";          # reranked result
$rrdir_best="$rrdir/best";        # best reranked result
`mkdir $rrdir_new` if (!-e $rrdir_new);
`mkdir $rrdir_best` if (!-e $rrdir_best);

$savedir= "$rdir/$qtype/rtmiss";
`mkdir $savedir` if (!-e "$savedir");


#-------------------------------------------------
# process form input from the result page
#-------------------------------------------------

if($qtype eq 'train'){
   $evalf = "/u1/trec/qrels/qrels.opinion.blog06-07";
   $qrelcnt = "/u3/trec/blog08/results/train/qrelcnt";
   @qns= (851..950);
}
else {
   $evalf = "/u1/trec/qrels/qrels.opinion.blog08";
   $qrelcnt = "/u3/trec/blog08/results/test/qrelcnt";
   @qns= (1001..1050);
}
(%evalstat,%eval) = ();

if($dtype =~ /^t/){
       &topic;
}
elsif($dtype =~ /^q/){
       &query;
}
else{
 
    my $head=`head -1 $rdir/$rfile`;
    chomp $head;
    my($qn,$bID,$rank0,$score,$group,@rest)= (split/\s+/,$head);
    $fsnum=@rest;

    #-------------------------------------------------
    # create %qrels
    #   - key=QN, val=pointer to docID
    #-------------------------------------------------
    if (-e $evalf) {
          # create qrels hash
          @lines = `grep '^$qnumber' $evalf`;
          chomp @lines;
          foreach(@lines){
               my($qn,$dummy,$dname,$relsc)= split(/\s+/,$_); #($qnumber 0 $dn $rel_score)
                $eval{$dname}=$relsc;
                if ($relsc > 0){
                    $topicrel ++;
                    if ($relsc > 1){
                        $opinionrel ++;
                    }
                }
          }
    } 

    
    #-------------------------------------------------
    # create %qrelcnt
    #   - $qrelcnt{$qn}{$rtype}=$relcnt
    #     where $rtype= topic | opinion
    #           $relcnt= number of known relevant document
    #-------------------------------------------------
    open(IN,$qrelcnt) || die "can't read $qrelcnt";
    @lines =<IN>;
    close IN;
    chomp @lines;
    foreach(@lines){
        my($qn,$reln1,$reln2)= split/\s+/; 
        $qrelcnt{$qn}{'topic'}=$reln1;
        $qrelcnt{$qn}{'opinion'}=$reln2;
    }

    #-------------------------------------------------
    # create %evalstat: original result eval stats
    #   - $evalstat{$qn}{$ename}=$estat
    #     where $ename= [ap|rp|pN][T|O]
    #              ap=avgp, rp=R_prec, T=topic, O=opinion
    #           $estat= eval score
    #-------------------------------------------------
    $evalstatf= "$rrdir/evalstat";
    open(IN,$evalstatf) || die "can't read $evalstatf";
    @lines =<IN>;
    close IN;
    chomp @lines;
    foreach(@lines){
        next if /^QN/;
        my($qn,@stats)= split/\s+/; 
        $evalstat{$qn}{'apT'}=$stats[0];
        $evalstat{$qn}{'rpT'}=$stats[1];
        $evalstat{$qn}{'p10T'}=$stats[2];
        $evalstat{$qn}{'p50T'}=$stats[3];
        $evalstat{$qn}{'p100T'}=$stats[4];
        $evalstat{$qn}{'apO'}=$stats[5];
        $evalstat{$qn}{'rpO'}=$stats[6];
        $evalstat{$qn}{'p10O'}=$stats[7];
        $evalstat{$qn}{'p50O'}=$stats[8];
        $evalstat{$qn}{'p100O'}=$stats[9];
    }

    #-------------------------------------------------
    # create %bwts: best rerank weights
    #   - k=wt_name, v=weight
    # create %bestRR: best rerank eval stat
    #   - k=eval_name, v=stat
    $bestrr= "$rrdir/rerank_best";
    if (-e $bestrr) {
        open(IN,$bestrr) || die "can't read $bestrr";
        @lines=<IN>;
        close IN;
        (%bwts)= split/\s+/,$lines[0]; 
        (%bestRR)= split/\s+/,$lines[1]; 
        if ($lines[2]=~/OLP/) { $OLPused=1; }
        elsif ($lines[2]) { 
            ($bwtgrp,%bwtsG)= split/\s+/,$lines[2]; 
            $OLPused=1 if ($lines[3]=~/OLP/);
        }
        else {
            %bwtsG= %bwts;
        }
    }

    #-------------------------------------------------
    # original rerank formula weight
    if ($rfile=~m|/s0R1/|) {
        %wts=(
        'origsc'=>0.85,'rrsc'=>0.15,
        'ex1'=>4.5,'ex2'=>3,'px1'=>3,'px2'=>2,'px3'=>1,'ph'=>4,'nr'=>3,'nr2'=>10,
        'ac'=>2.5,'hf'=>1,'iu'=>2,'lf'=>1.5,'w1'=>0.3, 'w2'=>0.2,'em'=>'0.2','in1'=>0.2,'in2'=>0.1,
        'acx'=>5,'hfx'=>2,'iux'=>4,'lfx'=>3,'w1x'=>0.6, 'w2x'=>0.4,'emx'=>'0.4',
        );
    }
    else {
        %wts=(
        'origsc'=>0.84,'rrsc'=>0.16,
            'in1'=>0.3,
            'in2'=>0.01,
            'av'=>0.01,
            'avx'=>0.02,
            'em'=>0.1,
            'ac'=>0.4,
            'hf'=>0.8,
            'iu'=>0.8,
            'lf'=>0.3,
            'w1'=>0.5,
            'w2'=>0.25,
            'emx'=>0.3,
            'acx'=>1.2,
            'hfx'=>2.4,
            'iux'=>2.4,
            'lfx'=>0.9,
            'w1x'=>1.5,
            'w2x'=>0.75,
            'emd'=>0.2,
            'acd'=>0.8,
            'hfd'=>1.6,
            'iud'=>1.6,
            'lfd'=>0.6,
            'w1d'=>1.0,
            'w2d'=>0.5,
        );
    }

    #-------------------------------------------------
    # rerank results
    #  1. read in rerank weights
    #  2. rerank in original rerank files with new weights
    #     - save output in saved subdir
    #-------------------------------------------------
    if ($submit=~/rerank|best/i) {

        if ($rfile=~/r1$/) {

            foreach $name('origsc','rrsc','ex1','ex2','wx1','wx2','px1','px2','px3','ph','nr','nr2') {
                $wts{"$name"}=param("$name");
                $wtsG{"$name"}=param("2$name");
            }
            if ($submit=~/best/i) {
                %wts=%bwts;
                %wtsG=%bwtsG;
                $wtgrp=$bwtgrp;
            }

            &revalrtall($rrdir,$rrdir_new,\@qns,'topic');

            # if reranked MAP is better, save to file and update %bwts
            if ($bestRR{'apT'}<$evalRR{'ALL'}{'apT'}) {
                open(OUT,">$bestrr") || die "can't write to $bestrr";
                print OUT &hash2str(\%wts),"\n";
                print OUT &hash2str($evalRR{'ALL'}),"\n";
                print OUT "$wtgrp ",&hash2str(\%wtsG),"\n";
                print OUT "OLP\n" if ($useolp);
                close OUT;
                %bwts=%wts;
                %bwtsG=%wtsG;
                $bwtgrp=$wtgrp;
                `cp $rrdir_new/* $rrdir_best/`;
            }
        }

        elsif ($rfile=~/r2$/) {

            foreach $name('origsc','rrsc',@vname2) {
                $wts{"$name"}=param("$name");
                $wtsG{"$name"}=param("2$name");
            }
            if ($submit=~/best/i) {
                %wts=%bwts;
                %wtsG=%bwtsG;
                $wtgrp=$bwtgrp;
            }

            &revalrtall($rrdir,$rrdir_new,\@qns,'opinion');

            # if reranked MAP is better, save to file and update %bwts
            if ($bestRR{'apO'}<$evalRR{'ALL'}{'apO'}) {
                open(OUT,">$bestrr") || die "can't write to $bestrr";
                print OUT &hash2str(\%wts),"\n";
                print OUT &hash2str($evalRR{'ALL'}),"\n";
                print OUT "$wtgrp ",&hash2str(\%wtsG),"\n";
                print OUT "OLP\n" if ($useolp);
                close OUT;
                %bwts=%wts;
                %bwtsG=%wtsG;
                `cp $rrdir_new/* $rrdir_best/`;
            }
        }

        elsif ($rfile=~/f$/) {

            for($i=1;$i<=$fsnum;$i++) {
                $wts{"fwt$i"}=param("fwt$i");
            }
            %wts=%bwts if ($submit=~/best/i);

            &revalrtall($rrdir,$rrdir_new,\@qns,'fusion');

            # if reranked MAP is better, save to file and update %bwts
            if (($rfile=~/1/ && $bestRR{'apT'}<$evalRR{'ALL'}{'apT'}) ||
                ($rfile=~/2/ && $bestRR{'apO'}<$evalRR{'ALL'}{'apO'})) {
                open(OUT,">$bestrr") || die "can't write to $bestrr";
                print OUT &hash2str(\%wts),"\n";
                print OUT &hash2str($evalRR{'ALL'}),"\n";
                close OUT;
                %bwts=%wts;
                `cp $rrdir_new/* $rrdir_best/`;
            }
        }

        # append rerank data to log
        open(OUT,">>$rrlogf") || die "can't append to $rrlogf";
        print OUT "$rfile\n";
        print OUT &hash2str(\%wts),"\n";
        print OUT &hash2str($evalRR{'ALL'}),"\n";
        print OUT "$wtgrp ",&hash2str(\%wtsG),"\n";
        close OUT;

        $resultf = "$rrdir/new/rt$qnumber";
    }
    else {
        $resultf = "$rrdir/rt$qnumber";
    }


    &result($resultf,\%eval);

    #write out the missing relevant docs
    &saveMiss(\%eval);
}


#---------------------------------------------------------------
# sub routines
#---------------------------------------------------------------

sub hash2str {
    my $hp=shift;
    my @list;
    foreach $name(sort keys %$hp) {
        my $val= $$hp{$name};
        $val=0 if (!defined($val));
        push(@list,"$name $$hp{$name}");
    }
    my $str=join(" ",@list);
    return $str;
} #endsub hash2str

#----------------------------------                                          
sub result {
   my ($inf,$eHash)= @_;

   #get the title of the topic
   my $query ="$qdir/$qtype/q$qnumber";
   open(IN,$query)||die"can't open $query";
   my @qlines = <IN>;
   chomp@qlines;
   close(IN);
   my $qline=join(' ',@qlines);
   $qline =~ /<text>(.*?)<\/text>/s;   
   $title = $1;   

   open(IN,$inf) || die "can't read $inf";
   my @rlines=<IN>;
   close IN;

   #DN relsc Rank SC GroupName RunName Rank_orig SC_orig extSC1 extSC2 prxSC1 prxSC2 prxSC3 phSC nrSC nrSC2
   #BLOG06-20051225-084-0003177858 2 1 1.4001819 g1 wdoqln0x 25 1.4700261 0 0 2.009 1.0045 0 0 0.2013
   foreach(@rlines){
        my($bID,$relsc,$rank0,$score)= split/\s+/;
        #last if(!$relonly ** $rank0>$maxrank);#!!NY
        $ids{$rank0}{$bID} = $_; 
        if(exists($$eHash{$bID}) && ($rank0 <=1000)){
             if ($$eHash{$bID} > 0){
                 $topicrel_ret ++;
             }
             if ($$eHash{$bID} > 1){
                 $opinionrel_ret ++;
             }
        }
   }

    if ($rfile=~/f$/) { &showpage_f($eHash); }
    elsif ($rfile=~/2$/) { &showpage_2($eHash); }
    elsif ($rfile=~/1$/) { &showpage_1($eHash); }
    else { &showpage($eHash); }


}#end sub result


# show topic reranking interface
sub showpage_1 {
    my $eHash=shift;
    print header();
    &startHTML();
    &show_eval;
    &show_formula1;

    $rdchk='checked' if ($relonly);
    $nrdchk='checked' if ($relonly0);

    print "
           <table border=1>
           <tr>
               <td colspan=5>Topic $qnumber: <b>$title</b><br>
                   Retrieved: On-topic:  <b>$topicrel_ret ($topicrel)</b>\; 
                   On-topic and opinion:  <b>$opinionrel_ret ($opinionrel)</b>  
               </td>
               <td colspan=10>
                <input type=checkbox name=relonly value=1 $rdchk><font size=-2>reldoc only, </font>
                <input type=checkbox name=relonly0 value=1 $nrdchk><font size=-2>non-reldoc only</font> &nbsp; &nbsp;
               <font size=1>
                   <b>SC</b>=rerankSC, <b>SC_ex1</b>=exactM(qTI-dTI), <b>SC_ex2</b>=exactM(qTI-dBD), 
                   <b>SC_px1</b>=proxM(qTI-dTI), <b>SC_px2</b>=proxM(qTI-dBD), <b>SC_px3</b>=proxM(qDesc-dBD), 
                   <b>SC_ph</b>=PhraseM, <b>SC_nr</b>=NonRelPhM, <b>SC_nr2</b>=NonrelNounM</font>
               </td></tr>
          <tr><td colspan=3> <a target='new' href='rdspBlog06_3a.cgi?qn=$qnumber&rfile=$rfile'>See the un-retrieved relevant docs</a> </td>
               <th>Assess</th>
               <th>Group</th>
               <th>SC</th>
               <th>SC_org</th>
               <th>SC_ex1</th>
               <th>SC_ex2</th>
               <th>SC_px1</th>
               <th>SC_px2</th>
               <th>SC_px3</th>
               <th>SC_ph</th>
               <th>SC_nr</th>
               <th>SC_nr2</th>
           </tr>
    ";

    foreach $rank(sort {$a<=>$b}keys %ids) {
       last if ($rank>$maxrank3);
       #last if ($rank>$maxrank);
       foreach $docno(keys %{$ids{$rank}}){
          if(exists($$eHash{$docno})){
              $trec_ass = $$eHash{$docno};
              # delete $$eHash{$docno}; 
              delete $eHash->{$docno};
          }
          else{
               $trec_ass = '-1';
          }
          my($bID,$relsc,$rank0,$score,$grp,$run,$rank_orig,$sc_orig,$extsc1,$extsc2,$prxsc1,$prxsc2,$prxsc3,$phsc,$nrsc,$nrsc2)= split/\s+/,$ids{$rank}{$docno};

          next if ($relonly && $trec_ass<1);  # show rel doc only
          next if ($relonly0 && $trec_ass>0);  # show nonrel doc only
          #next if ($relonly && $trec_ass<$relonly);
          #next if ($relonly0 && $trec_ass != $relonly0);
          printf "<tr>
               <td><a target='new' href='../showpml.cgi?doc=$docno&type=1'>$rank</a></td>
               <td>$rank_orig</td>
               <td><a target='new' href='../showpml.cgi?doc=$docno&type=2'>$docno</a></td>
               <td>$score_cl{$trec_ass}$trec_ass</font></td>
               <td>$grp</td>
               <td>%.4f</td>
               <td>%.4f</td>
               <td>%.3f</td>
               <td>%.3f</td>
               <td>%.3f</td>
               <td>%.3f</td>
               <td>%.3f</td>
               <td>%.3f</td>
               <td>%.3f</td>
               <td>%.3f</td>
               </tr>\n",$score,$sc_orig,$extsc1,$extsc2,$prxsc1,$prxsc2,$prxsc3,$phsc,$nrsc,$nrsc2;    
        }
    }
    print "</table>";
    print end_html();
} #endsub-showpage_1


# show opinion reranking interface
sub showpage_2 {
    my $eHash=shift;
    print header();
    &startHTML;
    &show_eval;
    &show_formula2;

    $rdchk='checked' if ($relonly);
    $nrdchk='checked' if ($relonly0);

    my $tip1= "<font size=-2>Found: <b>$opinionrel_ret ($opinionrel)</b> T&O &nbsp; <b>$topicrel_ret ($topicrel)</b> Tonly</font>";

    my $tip2= "<font size=1>
                 <b>SC</b>=rerankSC, <b>AC</b>=Acronym, <b>HF/LF</b>=High/LowFreq lex, <b>IU</b>=I-You lex, 
                 <b>W1, W2</b>=Wilson (strong/weak), <b>Em</b>=Wilson (emphasis),
                 <b>In1</b>=I count, <b>In2</b>=You/We count2, <b>*x</b>=Proximity, <b>*d</b>=Idist</font>";

    my $unretrieved= "<font size=-2><a target='new' href='$cgi?rsubd=$rsubd&qn=$qnumber&rfile=$rfile'>un-retrieved reldocs</a></font>";

    my $tooltip2=$tooltip;
    $tooltip2=~s/balloonNUM/balloonT/;
    $tooltip2=~s!TIP!$tip1!;

    my $tooltip3=$tooltip;
    $tooltip3=~s/balloonNUM/balloonSC/;
    $tooltip3=~s!TIP!$tip2!;

#<th>IU</th> <th>AC</th> <th>HF</th> <th>LF</th> <th>W1</th> <th>W2</th> <th>Em</th> <th>IUx</th> <th>ACx</th> <th>HFx</th> <th>LFx</th> <th>W1x</th> <th>W2x</th> <th>Emx</th> <th>IUd</th> <th>ACd</th> <th>HFd</th> <th>LFd</th> <th>W1d</th> <th>W2d</th> <th>Emd</th>

    print " $tooltip2 $tooltip3
           <table border=1>
           <tr>
               <td colspan=8><a target=new href='$cgi?rsubd=$rsubd&qt=$qtype&qn=$qnumber&dsptype=topic' rel='balloonT'>Q$qnumber</a>:  
               <font size=-1><b>$title</b></font>
               </td>
               <td colspan=23>
                <input type=checkbox name=relonly value=1 $rdchk><font size=-2>reldoc only, </font>
                <input type=checkbox name=relonly0 value=1 $nrdchk><font size=-2>non-reldoc only</font>
                <input type=submit name=submit value='Rerank'> <input type=submit name=submit value='Best'>
                &nbsp; &nbsp; 
                &nbsp; &nbsp; $unretrieved
                &nbsp; &nbsp; <a href='#10' rel='balloonSC'><font size=-1>LEGEND</font></a>
               </td>
          </tr>
          <tr><th colspan=2>Rank (old)</td>
               <th>Rel</th>
               <th>Grp</th>
               <th>SC</th>
               <th>SCorg</th>
               <th>In1</th>
               <th>In2</th>
               <th>AC</th>
               <th>ACx</th>
               <th>ACd</th>
               <th>IU</th>
               <th>IUx</th>
               <th>IUd</th>
               <th>LF</th>
               <th>LFx</th>
               <th>LFd</th>
               <th>HF</th>
               <th>HFx</th>
               <th>HFd</th>
               <th>W1</th>
               <th>W1x</th>
               <th>W1d</th>
               <th>W2</th>
               <th>W2x</th>
               <th>W2d</th>
               <th>Em</th>
               <th>Emx</th>
               <th>Emd</th>
               <th>AV</th>
               <th>AVx</th>
           </tr>
    ";


    foreach $rank(sort {$a<=>$b}keys %ids) {
       last if ($rank>1000);
       #last if ($rank>$maxrank3);
       foreach $docno(keys %{$ids{$rank}}){
          if(exists($$eHash{$docno})){
              $trec_ass = $$eHash{$docno};
              # delete $$eHash{$docno}; 
              delete $eHash->{$docno};
          }
          else{
               $trec_ass = '-1';
          }
          my($bID,$relsc,$rank0,$score,$grp,$run,$rank_orig,$sc_orig,@opscs)=split/\s+/,$ids{$rank}{$docno};

            # read opinion scores into %sc
            my %sc;
            my $index=0;
            foreach $name(@vnameOP) {
                $sc{$name}=$opscs[$index];
                #print "$name=$opscs[$index],";
                $index++;
            }
            #print "<br>"; exit if ($cnt++>20);

          next if ($relonly && $trec_ass<2);  # show rel doc only
          next if ($relonly0 && $trec_ass>1);  # show nonrel doc only
          #next if ($relonly && $trec_ass<$relonly);
          #next if ($relonly0 && $trec_ass != $relonly0);

          my $tooltip2=$tooltip;
          $tooltip2=~s/balloonNUM/balloon$rank/;
          $tooltip2=~s/>TIP</>$docno</;

          printf "<tr>
               <td><font size=-1><a target='new' href='../showpml.cgi?doc=$docno&type=1' rel='balloon$rank'>$rank</a>$tooltip2</font></td>
               <td><font size=-1><a target='new' href='../showpml.cgi?doc=$docno&type=2' rel='balloon$rank'>$rank_orig</a></font></td>
               <td><font size=-1>$score_cl{$trec_ass}$trec_ass</font></font></td>
               <td><font size=-1>$grp</font></td>
               <td><font size=-1>%.3f</font></td> <td><font size=-1>%.3f</font></td>\n",$score,$sc_orig;

            foreach $name(@vname2) {
                if ($name=~/d$/) {
                #if ($name=~/iu|lf/i) {
                    printf "<td><font color=green size=-1>%.3f</font></td>",$sc{$name}*10;  # multiply by 10 for display
                }
                else {
                    printf "<td><font size=-1>%.3f</font></td>",$sc{$name}*10;  # multiply by 10 for display
                }
            }
         print "</tr>\n";
        }
    }
    print "</table></form>";
    print end_html();
} #endsub-showpage_2


sub showpage_f {
    my $eHash=shift;
    print header();
    &startHTML;
    &show_eval;
    &show_formulaf;

    my $cspan=$fsnum+2;

    print "
           <table border=1>
           <tr>
               <td colspan=3>Topic $qnumber: <b>$title</b><br>
                   Retrieved: On-topic:  <b>$topicrel_ret ($topicrel)</b>\; 
                   On-topic and opinion:  <b>$opinionrel_ret ($opinionrel)</b>  
               </td>
               <td colspan=$cspan><font size=1><b>SC</b>=rerankSC, <b>Group</b>=rerank group, <b>Rank_Run_Grp</b>=fusion sources</font>
           </td>
          </tr>
          <tr><td colspan=2> <a target='new' href='rdspBlog06_3a.cgi?qn=$qnumber&rfile=$rfile'>See the un-retrieved relevant docs</a> </td>
               <th>Assess</th>
               <th>SC</th>
               <th>Group</th>
               <th colspan=$fsnum>Rank_Run_Grp</th>
           </tr>
    ";

    foreach $rank(sort {$a<=>$b}keys %ids) {
       last if ($rank>$maxrank3);
       foreach $docno(keys %{$ids{$rank}}){
          if(exists($$eHash{$docno})){
              $trec_ass = $$eHash{$docno};
              delete $eHash->{$docno};
              #delete $$eHash{$docno}; 
          }
          else{
               $trec_ass = '-1';
          }
          #my($qn,$bID,$rank0,$score,$rest)= split/\s+/,$ids{$rank}{$docno},5;
          my($bID,$relsc,$rank0,$score,$group,$rest)= split/\s+/,$ids{$rank}{$docno},6;
          #$rest=~s/ /&nbsp; &nbsp;/g;
          my@scores= split/ +/,$rest;
          next if ($relonly && $trec_ass<$relonly);
          next if ($relonly0 && $trec_ass != $relonly0);
          printf "<tr>
               <td><a target='new' href='../showpml.cgi?doc=$docno&type=1'>$rank</a></td>
               <td><a target='new' href='../showpml.cgi?doc=$docno&type=2'>$docno</a></td>
               <td>$score_cl{$trec_ass}$trec_ass</font></td>
               <td>%.4f</td>
               <td>$group</td>
               ",$score;
          foreach $str(@scores) {
              my($sc,$rgg)=split/:/,$str;
              printf " <td>%.4f ($rgg)</td>",$sc;
          }
          print "</tr>\n";
        }
    }
    print "</table>";
    print end_html();
} #endsub-showpage_f


sub startHTML {
    print "<html>
           <head>
           <link rel='stylesheet' type='text/css' href='balloontip.css' />

           <script type='text/javascript' src='balloontip.js'>

           /***********************************************
           * Rich HTML Balloon Tooltip- � Dynamic Drive DHTML code library (www.dynamicdrive.com)
           * This notice MUST stay intact for legal use
           * Visit Dynamic Drive at http://www.dynamicdrive.com/ for full source code
           ***********************************************/

           </script>
           </head>
           <body>\n";
}


sub showpage {
    my $eHash=shift;
    print header();
    &startHTML;
    print "<table border=1>
           <tr>
               <td colspan=3>Topic $qnumber: <b>$title</b><br>
                   Retrieved: On-topic:  <b>$topicrel_ret ($topicrel)</b>\; 
                   On-topic and opinion:  <b>$opinionrel_ret ($opinionrel)</b>  
               </td>
               <td>&nbsp;
           </td>
          </tr>
          <tr><td colspan=2> <a target='new' href='rdspBlog06_3a.cgi?qn=$qnumber&rfile=$rfile'>See the un-retrieved relevant docs</a> </td>
               <th>Assess</th>
               <th>SC</th>
           </tr>
    ";

    foreach $rank(sort {$a<=>$b}keys %ids) {
       foreach $docno(keys %{$ids{$rank}}){
          if(exists($$eHash{$docno})){
              $trec_ass = $$eHash{$docno};
              delete $eHash->{$docno};
              #delete $$eHash{$docno}; 
          }
          else{
               $trec_ass = '-1';
          }
          #my($qn,$dummy,$bID,$rank0,$score)= split/\s+/,$ids{$rank}{$docno};
          my($bID,$relsc,$rank0,$score)= split/\s+/,$ids{$rank}{$docno};
          $rest=~s/ /&nbsp; &nbsp;/g;
          next if ($relonly && $trec_ass<$relonly);
          next if ($relonly0 && $trec_ass != $relonly0);
          printf "<tr>
               <td><font size=-1><a target='new' href='../showpml.cgi?doc=$docno&type=1'>$rank</a></font></td>
               <td><font size=-1>$rank_orig</font></td>
               <td><font size=-2><a target='new' href='../showpml.cgi?doc=$docno&type=2'>$docno</a></font></td>
               <td><font size=-1>$score_cl{$trec_ass}$trec_ass</font></td>
               <td><font size=-1>%.4f</td>
               </tr>\n",$score;    
        }
    }
    print "</table>";
    print end_html();
} #endsub-showpage_f


#----------------------------------                                          
sub topic {

    if($qtype eq 'train'){
        $topic = "$tdir/06-07.blog-topics";
    }
    else{
        $topic = "$tdir/08.blog-topics";
    }

    # get the original topic
    open(IN,$topic) || die "can't read $topic";  
    @lines=<IN>;                
    close IN;      
    $lines= join("",@lines);
    $lines=~s/\&/and/g;

    $lines=~m|(<num> Number: $qnumber.+?</top>)|s;
    $topic_lines="<top>\n".$1;
    $topic_lines=~s|(<title>)|</num>$1| if ($topic_lines!~m|</num>|i);
    $topic_lines=~s|(<desc>)\s*Description:|</title>$1| if ($topic_lines!~m|</title>|i);
    $topic_lines=~s|(<narr>)\s*Narrative:|</desc>$1| if ($topic_lines!~m|</desc>|i);            
    $topic_lines=~s|(</top>)|</narr>$1| if ($topic_lines!~m|</narr>|i);

    print header(-type=>"text/xml");
    print $topic_lines;

} #end sub  topic

#----------------------------------                                          
sub query {
    $rfile =~m|([^/]+)$|;
    $run = $1;
    #okapi_qs.r2
    $run =~ m|^\w+?\_([^.]+)\.?|;
    $qid = $1;

    my $query = "$qdir/$qtype/s0/$qid$qnumber";
    if(!-e $query){ $qid =~ s/^(.+?)\w$/$1/; }

    $query = "$qdir/$qtype/s0/$qid$qnumber";
    if(!-e $query){ $query= "$qdir/$qtype/s0gg2/qsxm$qnumber.30"; }

    # get the query
    open(IN,$query) || die "can't read $query";  
    @lines=<IN>;        
    chomp (@lines);        
    close IN;      
    $big_line = join("<br>",@lines);
    $big_line = "<h3>qn: $qnumber</h3>".$big_line;

    print header(-type=>"text/html");
    print start_html();
    print $big_line;
    print end_html();

} #endsub query


#--------------------------------------------
# save the missing relevant docs
#--------------------------------------------
#   arg1 = run name
#   arg2 = topic number
#   arg3 = pointer to eval hash
#--------------------------------------------
sub saveMiss {
    my($hp)=@_;
    $rfile =~ /^.*\/([^\/]*)$/;
    $run = $1;
    if($rfile =~ /trecfmtx/){
         $run.='x';
    }
    $file = "$savedir/$run".'_'.$qnumber; 
    open(OUT,">$file") || die "can't write to $file";
    foreach $dn(sort {$$hp{$b}<=>$$hp{$a}} keys %$hp) {
        if($$hp{$dn} <=0){last;} 
        print OUT "$dn $$hp{$dn}\n";
    }
    close OUT;
} #endsub saveMiss


#--------------------------------------------
# display performance stats
#--------------------------------------------
sub show_eval {

    my $olpused= "(OLP)" if ($useolp);

    my(@name);
    foreach my$name('MAP','MRP','P\@10','P\@50','P\@100') {
        push(@name,"<th><font size=-1>$name</font>");
    }
    my $thstr= join("",@name);

    my(@nameaT,@nameaO,,@namearT,@namearO,@nameqT,@nameqO,@nameqrT,@nameqrO);
    foreach my$name('ap','rp','p10','p50','p100') {
        my ($namet,$nameo)= ($name.'T',$name.'O');
        push(@nameaT,"<td><font size=-1>$evalstat{'ALL'}{$namet}</font>");
        push(@nameaO,"<td><font size=-1>$evalstat{'ALL'}{$nameo}</font>");
        if ($evalRR{'ALL'}{$nameo}>$evalstat{'ALL'}{$nameo}) {
            push(@namearO,"<td><font color=purple size=-1><b>$evalRR{'ALL'}{$nameo}</b></font>");
        }
        else { push(@namearO,"<td><font size=-1>$evalRR{'ALL'}{$nameo}</font>"); }
        if ($evalRR{'ALL'}{$namet}>$evalstat{'ALL'}{$namet}) {
            push(@namearT,"<td><font color=purple size=-1><b>$evalRR{'ALL'}{$namet}</b></font>");
        }
        else { push(@namearT,"<td><font size=-1>$evalRR{'ALL'}{$namet}</font>"); }
        push(@nameqT,"<td><font size=-1>$evalstat{$qnumber}{$namet}</font>");
        push(@nameqO,"<td><font size=-1>$evalstat{$qnumber}{$nameo}</font>");
        push(@nameqrT,"<td><font size=-1>$evalRR{$qnumber}{$namet}</font>");
        push(@nameqrO,"<td><font size=-1>$evalRR{$qnumber}{$nameo}</font>");
    }
    my $thstr= join("",@name);
    my $alltstr= join("",@nameaT);
    my $allostr= join("",@nameaO);
    my $allrtstr= join("",@namearT);
    my $allrostr= join("",@namearO);
    my $qtstr= join("",@nameqT);
    my $qostr= join("",@nameqO);
    my $qrtstr= join("",@nameqrT);
    my $qrostr= join("",@nameqrO);


    # column headings for performance stats
    print "
    <table border=1>
    <tr>
        <th>&nbsp;<th colspan=11><i>--- Original ---</i>
        <th>&nbsp;<th colspan=11><i>--- Reranked ---<i> $olpused
    <tr>
    <tr>
        <th>&nbsp;<th colspan=5>Topic<th>&nbsp;<th colspan=5>Opinion
        <th>&nbsp;<th colspan=5>Topic <font size=-2>(bestMAP=$bestRR{'apT'})</font><th>&nbsp;<th colspan=5>Opinion <font size=-2>(bestMAP=$bestRR{'apO'}</font>)
    <tr>
        <th>&nbsp $thstr <th>&nbsp $thstr <th>&nbsp $thstr <th>&nbsp $thstr
    <tr>
        <td><b><font size=-1>All Topics</font></b>
        $alltstr <td>&nbsp; $allostr <td>&nbsp;
        $allrtstr <td>&nbsp; $allrostr <td>&nbsp;
    <tr>
        <td><b>Q$qnumber</b>
        $qtstr <td>&nbsp; $qostr <td>&nbsp;
        $qrtstr <td>&nbsp; $qrostr <td>&nbsp;
    </table>
    ";

} #endsub show_eval


#---------------------------------------------
# display fusion formula: topic reranking
#---------------------------------------------
sub show_formula1 {

    # if not reranking and best wts exist, show them in the formula
    my (%wts2,%wtsG2);
    if ($submit!~/rerank|best/i && $bwts{'origsc'}) { %wts2=%bwts; %wtsG2=%bwtsG; }
    else { %wts2=%wts; %wtsG2=%wtsG; }

    my @vname=('ex1','ex2','px1','px2','px3','ph');
    my (@oform,@bform,@form,@form2);
    foreach my$name(@vname) { 
        push(@form,"<input type=text size=2 name=$name value=$wts2{$name}>*$name");
        push(@form2,"<input type=text size=2 name=2$name value=$wtsG2{$name}>*$name");
        push(@oform,"$wts{$name}*$name"); 
        push(@bform,"$bwts{$name}*$name"); 
    }
    my $oformstr= join(" + ",@oform);
    $oformstr = "($oformstr) - $wts{'nr'}*nr - $wts{'nr2'}*nr2";
    my $bformstr= join(" + ",@bform);
    $bformstr = "($bformstr) - $bwts{'nr'}*nr - $bwts{'nr2'}*nr2";
    my $formstr= join(" + ",@form);
    $formstr = "($formstr) - 
                <input type=text size=2 name=nr value=$wts2{'nr'}>*nr -
                <input type=text size=2 name=nr2 value=$wts2{'nr2'}>*nr2";
    my $formstr2= join(" + ",@form2);
    $formstr2 = "($formstr2) - 
                <input type=text size=2 name=2nr value=$wts2{'nr'}>*nr -
                <input type=text size=2 name=2nr2 value=$wts2{'nr2'}>*nr2";

    print "
    <form action=$cgi>
    <input type=hidden name=rsubd value='$rsubd'>
    <input type=hidden name=rfile value='$rfile'>
    <input type=hidden name=qn value='$qnumber'>
    <input type=hidden name=qt value='$qtype'>
    <input type=hidden name=dsptype value='$dtype'>
    <table border=0>
    ";

    # after rerank optimization, modify to get the optimized weights
    if ($rfile=~m|/s0R1/|) {  
        print "<tr><td colspan=2><b>Orig</b>: $wts{'origsc'}*sc' + $wts{'rrsc'}*$oformstr &nbsp;";
    }
    else {
        print "<tr><td colspan=2><b>Orig</b>: $wts{'origsc'}*sc' + $wts{'rrsc'}*$oformstr &nbsp;";
    }

    print "
    <tr><td colspan=2><b>BestRR</b>: $bwts{'origsc'}*sc' + $bwts{'rrsc'}*$bformstr
    <tr><td colspan=2><input type=submit name=submit value='Rerank'> 
                      <input type=submit name=submit value='Best'>: 
        <input type=text size=2 name=origsc value=$wts2{'origsc'}>*sc_norm + 
        <input type=text size=2 name=rrsc value=$wts2{'rrsc'}>*$formstr<br>
        Rank Group <input type=text size=1 name=wtgrp value='B'> : $formstr2
    </table></form><br>
    ";

}


#---------------------------------------------
# display fusion formula: opinion reranking
#---------------------------------------------
sub show_formula2 {

    # if not reranking and best wts exist, show them in the formula
    my (%wts2,%wtsG2);
    if ($submit!~/rerank|best/i && $bwts{'origsc'}) { %wts2=%bwts; %wtsG2=%bwtsG; }
    else { %wts2=%wts; %wtsG2=%wtsG; }

    my $olpused='OLP' if ($OLPused);

    my @vname2=('in1','in2','ac','acx','acd','iu','iux','iud','lf','lfx','lfd','hf','hfx','hfd','w1','w1x','w1d','w2','w2x','w2d','em','emx','emd','av','avx');

    my (@oform,@oform2,@bform,@bform2,@name,@input,@input2);
    foreach my$name(@vname2) { 
        push(@oform,"$wts{$name}*$name"); 
        push(@oform2,"$wtsG{$name}*$name"); 
        push(@bform,"$bwts{$name}*$name"); 
        push(@bform2,"$bwtsG{$name}*$name"); 
        push(@name,"<td>$name"); 
        # for formula input display
        push(@input,"<td><font size=1><input type=text size=1 name=$name value=$wts2{$name}>");
        push(@input2,"<td><font size=1><input type=text size=1 name='2$name' value='$wtsG2{$name}'>");
    }
    my $oformstr= join("+",@oform);
    my $oformstr2= join("+",@oform2);
    my $bformstr= join("+",@bform);
    my $bformstr2= join("+",@bform2);
    my $opnamestr= join("+",@name);
    my $wtstr= join("",@input);
    my $wtstr2= join("",@input2);

    print "
    <form action=$cgi>
    <input type=hidden name=rsubd value='$rsubd'>
    <input type=hidden name=rfile value='$rfile'>
    <input type=hidden name=qn value='$qnumber'>
    <input type=hidden name=qt value='$qtype'>
    <input type=hidden name=dsptype value='$dtype'>
    <table width=100% border=0>
    <tr><td colspan=2><b>Orig</b>: <font size=-1>$wts{'origsc'}*sc' + $wts{'rrsc'}*($oformstr)<br>
                $wtgrp: $wtsG{'origsc'}*sc' + $wtsG{'rrsc'}*($oformstr2)</font>
    <tr><td colspan=2><b>BestRR</b>: <font size=-1>$bwts{'origsc'}*sc' + $bwts{'rrsc'}*($bformstr) 
                $wtgrp:  $bwtsG{'origsc'}*sc' + $bwtsG{'rrsc'}*($bformstr2) &nbsp; $olpused</font>
    <tr><td>
        <table border=1>
        <tr><td><font size=1>Grp: O_SC+<td><font size=1>rrSC*($opnamestr) <td> <font size=1>OLP
        <tr><td><font size=1><b>A</b>: <input type=text size=1 name=origsc value=$wts2{'origsc'}>
            <td><font size=1><input type=text size=1 name=rrsc value=$wts2{'rrsc'}>$wtstr
            <td><font size=1><input type=checkbox name=useolp value=1>
        <tr><td><font size=1><input type=text size=1 name=wtgrp value=$wtgrp>:
                <input type=text size=1 name=2origsc value=$wtsG2{'origsc'}>
            <td><font size=1><input type=text size=1 name=2rrsc value=$wtsG2{'rrsc'}>$wtstr2
            <td>&nbsp;
        </table>
    </table><br>
    ";

}


#----------------------------------
# 1. for each query
#    a. generate reranked result
#    b. compute eval stats
# 2. create evalstat file
# 3. create %evalRR
#      $evalRR{$qn}{$ename}=$estat
#----------------------------------
# arg1= rerank input directory
# arg2= rerank output directory
# arg3= pointer to QN array
# arg4= rerank type (topic, opinion)
#----------------------------------
sub revalrtall {
    my($ind,$outd,$qnlp,$rtype)=@_;

    my ($qcnt,%evaltot)=(0);

    my $evalf= "$outd/evalstat";
    open(EVALF,">$evalf") || die "can't write to $evalf";
    print EVALF "QN AP_topic RP_topic P10_topic P50_topic p100_topic AP_op RP_op P10_op P50_op P100_op\n";

    foreach $qn(@$qnlp) {

        #next if (!$qrelcnt{$qn}{$rtype});

        my $inf="$ind/rt$qn";
        my $outf="$outd/rt$qn";

        my %evals= &revalrt($qn,$inf,$outf,$rtype);

        printf EVALF "$qn %.4f %.4f %.4f %.4f %.4f %.4f %.4f %.4f %.4f %.4f\n",
                        $evals{'apT'},$evals{'rpT'},$evals{'p10T'},$evals{'p50T'},$evals{'p100T'},
                        $evals{'apO'},$evals{'rpO'},$evals{'p10O'},$evals{'p50O'},$evals{'p100O'};

        foreach $eval(keys %evals) {
            $evaltot{$eval} += $evals{$eval};
            $evalRR{$qn}{$eval}= $evals{$eval};
        }
        $qcnt++;

    }

    foreach $eval(keys %evaltot) {
        $evaltot{$eval}= sprintf("%.4f",$evaltot{$eval}/$qcnt);
        $evalRR{'ALL'}{$eval}= $evaltot{$eval};
    }
    printf EVALF "ALL %.4f %.4f %.4f %.4f %.4f %.4f %.4f %.4f %.4f %.4f\n",
            $evaltot{'apT'},$evaltot{'rpT'},$evaltot{'p10T'},$evaltot{'p50T'},$evaltot{'p100T'},
            $evaltot{'apO'},$evaltot{'rpO'},$evaltot{'p10O'},$evaltot{'p50O'},$evaltot{'p100O'};
    close EVALF;

} #endsub revalrtall


#----------------------------------
# for a given query
#    a. generate reranked result
#    b. compute eval stats
#----------------------------------
# arg1= query number
# arg2= input (original result) file
# arg3= output (reranked result) file
# arg4= rerank type (topic, opinion)
#----------------------------------
sub revalrt {
    my($qn,$in,$out,$rtype)=@_;

    open(IN,$in) || die "can't read $in";
    my @lines=<IN>;
    close IN;

    if ($rtype eq 'topic') {
        &rerank1($qn,$out,\@lines);
    }
    elsif ($rtype eq 'opinion') {
        &rerank2($qn,$out,\@lines);
    }

    my %evals= &evalstat($qn,$out);

    return (%evals);

} #endsub revalrt


#----------------------------------
# rerank rt results - topic reranking
#----------------------------------
# arg1= query number of current result
# arg2= pointer to output file
# arg3= pointer to input result array
#----------------------------------
sub rerank1 {
    my ($qn,$out,$inlp)=@_;

    # create reranking hashes by group 
    #  - %result1: exact match, qtitle to doc. title & doc. body
    #  - %result2: exact match, qtitle to doc. title
    #  - %result3: exact match, qtitle to doc. body
    #  - %result4: rest reranked
    #  - %result5: rest no reranked
    #  - key=docno, val=score
    my(%result0,%result1,%result2,%result3,%result4,%result5,%result6)=();

    foreach $line(@$inlp) {
        chomp $line;
        my ($docno,$relsc,$rank,$sc,$grp,$run,$oldrank,$oldsc,$extsc1,$extsc2,$prxsc1,$prxsc2,$prxsc3,$phsc,$nrsc,$nrsc2)=split/\s+/,$line;

        $result0{$docno}=$line;

        my ($olp,$olp2)=(1,0);
        $olp2++ if ($extsc1 || $extsc2);
        $olp2++ if ($prxsc1 || $prxsc2 || $prxsc3);
        $olp2++ if ($phsc);
        #$phsc *=2 if ($phsc && $olp2==1);
        #foreach $sc($extsc1,$extsc2,$prxsc1,$prxsc2,$prxsc3,$phsc) {
        #    $sc *=2 if ($sc && $olp2==1);
        #}
        #$useolp=1;
        if ($useolp) {
            $olp= ($olp+$olp2)/2;
        }

        # fusion score for on-topic score boosting
        #  - add to (normalized original score)*0.5
        my $score= $wts{'origsc'}*$sc + 
                   $wts{'rrsc'}*($olp*($wts{'ex1'}*$extsc1 + $wts{'ex2'}*$extsc2 + $wts{'px1'}*$prxsc1 + 
                                 $wts{'px2'}*$prxsc2 + $wts{'px3'}*$prxsc3 + $wts{'ph'}*$phsc)) 
                                 - $wts{'nr'}*$nrsc - $wts{'nr2'}*$nrsc2;

        # flag multi-term query
        #my $qphrase=0;
        #$qphrase=1 if ($qtitle{$qnum}=~/ /);
            
        # reranking groups:
        #  1 = exact match (qtitle to doc. title & body)
        #  2 = exact match (multi-term qtitle to doc. title only)
        #  3 = exact match (qtitle to doc. body only)
        #  4 = other
        # NOTE: results below maxrank is reranked as last group as default (diff. in rerank24)
        if ($rank<=$maxrank) {
            if ($grp=~/1$/) { $result1{$docno}=$score; }
            elsif ($grp=~/2$/) { $result2{$docno}=$score; }
            elsif ($grp=~/3$/) { $result3{$docno}=$score; }
            elsif ($grp=~/4$/) { $result4{$docno}=$score; }
            else { $result5{$docno}=$score; }
        }
        else { $result6{$docno}=$score; }

     } #end-foreach $line

    #-----------------------------------
    # rerank results by group and output
    #-----------------------------------

    open(OUT,">$out") || die "can't write to $out";

    my ($rank,$rank2,$score,$offset,$oldsc)=(0,0,0,0,1);

    foreach $docno(sort {$result1{$b}<=>$result1{$a}} keys %result1) {
        $score= sprintf("%.7f",$result1{$docno});
        my ($docno0,$relsc,$rank0,$sc0,$rest)=split(/\s+/,$result0{"$docno"},5);
        $rank++;
        # convert zero/negative score to non-zero value
        if ($score<=0) { $score= sprintf("%.7f",$oldsc-$oldsc*0.1); }
        print OUT "$docno $relsc $rank $score $rest\n";
        $oldsc=$score;
    }

    $rank2=1;
    $offset=0;
    foreach $docno(sort {$result2{$b}<=>$result2{$a}} keys %result2) {
        # offset: to ensure correct sorting/ranking for the whole result
        if ($rank2==1 && $result2{$docno}>$score) {
            $score -= $score*0.1;
            $offset= $score/$result2{$docno};
            print STDOUT "$docno: sc1=$result2{$docno}, sc2=$score, off=$offset\n" if ($debug);
        }
        if ($offset) { $score= sprintf("%.7f",$result2{$docno}*$offset); }
        else { $score= sprintf("%.7f",$result2{$docno}); }
        my ($docno0,$relsc,$rank0,$sc0,$rest)=split(/\s+/,$result0{"$docno"},5);
        $rank++;
        # convert zero/negative score to non-zero value
        if ($score<=0) { $score= sprintf("%.7f",$oldsc-$oldsc*0.1); }
        print OUT "$docno $relsc $rank $score $rest\n";
        $rank2++;
        $oldsc=$score;
    }

    $rank2=1;
    $offset=0;
    foreach $docno(sort {$result3{$b}<=>$result3{$a}} keys %result3) {
        # offset: to ensure correct sorting/ranking for the whole result
        if ($rank2==1 && $result3{$docno}>$score) {
            $score -= $score*0.1;
            $offset= $score/$result3{$docno};
            print STDOUT "$docno: sc1=$result3{$docno}, sc2=$score, off=$offset\n" if ($debug);
        }
        if ($offset) { $score= sprintf("%.7f",$result3{$docno}*$offset); }
        else { $score= sprintf("%.7f",$result3{$docno}); }
        my ($docno0,$relsc,$rank0,$sc0,$rest)=split(/\s+/,$result0{"$docno"},5);
        $rank++;
        # convert zero/negative score to non-zero value
        if ($score<=0) { $score= sprintf("%.7f",$oldsc-$oldsc*0.1); }
        print OUT "$docno $relsc $rank $score $rest\n";
        $rank2++;
        $oldsc=$score;
    }

    $rank2=1;
    $offset=0;
    foreach $docno(sort {$result4{$b}<=>$result4{$a}} keys %result4) {
        # offset: to ensure correct sorting/ranking for the whole result
        if ($rank2==1 && $result4{$docno}>$score) {
            $score -= $score*0.1;
            $offset= $score/$result4{$docno};
            print STDOUT "$docno: sc1=$result4{$docno}, sc2=$score, off=$offset\n" if ($debug);
        }
        if ($offset) { $score= sprintf("%.7f",$result4{$docno}*$offset); }
        else { $score= sprintf("%.7f",$result4{$docno}); }
        my ($docno0,$relsc,$rank0,$sc0,$rest)=split(/\s+/,$result0{"$docno"},5);
        $rank++;
        # convert zero/negative score to non-zero value
        if ($score<=0) { $score= sprintf("%.7f",$oldsc-$oldsc*0.1); }
        print OUT "$docno $relsc $rank $score $rest\n";
        $rank2++;
        $oldsc=$score;
    }

    $rank2=1;
    $offset=0;
    foreach $docno(sort {$result5{$b}<=>$result5{$a}} keys %result5) {
        # offset: to ensure correct sorting/ranking for the whole result
        if ($rank2==1 && $result5{$docno}>$score) {
            $score -= $score*0.1;
            $offset= $score/$result5{$docno};
            print STDOUT "$docno: sc1=$result5{$docno}, sc2=$score, off=$offset\n" if ($debug);
        }
        if ($offset) { $score= sprintf("%.7f",$result5{$docno}*$offset); }
        else { $score= sprintf("%.7f",$result5{$docno}); }
        my ($docno0,$relsc,$rank0,$sc0,$rest)=split(/\s+/,$result0{"$docno"},5);
        $rank++;
        # convert zero/negative score to non-zero value
        if ($score<=0) { $score= sprintf("%.7f",$oldsc-$oldsc*0.1); }
        print OUT "$docno $relsc $rank $score $rest\n";
        $rank2++;
        $oldsc=$score;
    }

    $rank2=1;
    $offset=0;
    foreach $docno(sort {$result6{$b}<=>$result6{$a}} keys %result6) {
        # offset: to ensure correct sorting/ranking for the whole result
        if ($rank2==1 && $result6{$docno}>$score) {
            $score -= $score*0.1;
            $offset= $score/$result6{$docno};
            print STDOUT "$docno: sc1=$result6{$docno}, sc2=$score, off=$offset\n" if ($debug);
        }
        if ($offset) { $score= sprintf("%.7f",$result6{$docno}*$offset); }
        else { $score= sprintf("%.7f",$result6{$docno}); }
        my ($docno0,$relsc,$rank0,$sc0,$rest)=split(/\s+/,$result0{"$docno"},5);
        $rank++;
        # convert zero/negative score to non-zero value
        if ($score<=0) { $score= sprintf("%.7f",$oldsc-$oldsc*0.1); }
        if ($rest) { print OUT "$docno $relsc $rank $score $rest\n"; }
        else { print OUT "$docno $relsc $rank $score\n"; }
        $rank2++;
        $oldsc=$score;
    }

    close OUT;

} #endsub rerank1


#----------------------------------
# rerank rt results - opinion reranking
#----------------------------------
# arg1= query number of current result
# arg2= pointer to output file
# arg3= pointer to input result array
#----------------------------------
sub rerank2 {
    my ($qn,$out,$inlp)=@_;

    # create reranking hashes by group 
    #  - %result1: exact match, qtitle to doc. title & doc. body
    #  - %result2: exact match, qtitle to doc. title
    #  - %result3: exact match, qtitle to doc. body
    #  - %result4: rest reranked
    #  - %result5: rest not reranked
    #  - key=docno, val=score

    my(%result0,%result1,%result2,%result3,%result4,%result5,@rest);

    # opinion score order in result file
    #   in1,in2,e,ex,ac,hf,iu,lf,w1,w2,acx,hfx,iux,lfx,w1x,w2x,
    #   acP,acN,hfP,hfN,iuP,iuN,lfP,lfN,w1P,w1N,w2P,w2N,
    #   acxP,acxN,hfxP,hfxN,iuxP,iuxN,lfxP,lfxN,w1xP,w1xN,w2xP,w2xN
    my @vname0=('ac','hf','iu','lf','acx','hfx','iux','lfx','acd','hfd','iud','lfd');


    foreach $line(@$inlp) {
        chomp $line;
        my ($docno,$relsc,$rank,$sc,$grp,$run,$oldrank,$origsc,@opscs)=split/\s+/,$line;

        $result0{$docno}=$line;

        # read opinion scores into %sc
        my %sc;
        my $index=0;
        foreach $name(@vnameOP) {
            $sc{$name}=$opscs[$index];
            $index++;
        }

        my ($olp,$olp2)=(1,0);
        foreach $name(@vname0) {
            $olp2++ if ($sc{$name}>0);
        }
        #$olp2++ if ($avsc || $avsc2);
        #!! try uncommenting
        #foreach $sc(@vnameOP) {
        #    $sc{$name}=0 if ($sc{$name} && $olp2==1);
        #}
        #$avsc=0 if ($avsc && $olp2==1);
        #$avsc=0 if ($avsc && $olp2==1 && $grp=~/C2/);
        if ($useolp) {
            $olp= ($olp+$olp2)/2;
        }

        my ($origwt,$rrwt);
        if ($wtgrp && ($grp ge $wtgrp)) { 
            $grprflag=1; 
            $origwt= $wtsG{'origsc'};
            $rrwt= $wtsG{'rrsc'};
        }
        else { 
            $grprflag=0; 
            $origwt= $wts{'origsc'};
            $rrwt= $wts{'rrsc'};
        }

        #!! modifed 11/17/08 to allow rank-group based fusion weights
        my ($opsc)=(0);  
        foreach $name(@vnameOP) {
            if ($grprflag) { $opsc += $wtsG{$name}*$sc{$name}; }
            else { $opsc += $wts{$name}*$sc{$name}; }
        }
        
        # fusion score for on-topic score boosting
        #  - add to (normalized original score)*0.5
        my $score= $origwt*$origsc + $rrwt*($olp*$opsc);
        #my $score= $origwt*$sc + $rrwt*($olp*$opsc);

        if ($rank<=$maxrank) {
            if ($grp=~/A/) { $result1{$docno}=$score; }
            elsif ($grp=~/B/) { $result2{$docno}=$score; }
            elsif ($grp=~/C/) { $result3{$docno}=$score; }
            else { $result4{$docno}=$score; }
        }
        else { 
            $result5{$docno}=$score2; 
            push(@rest,$docno);
        }

     } #end-foreach $line

    #-----------------------------------
    # rerank results by group and output
    #-----------------------------------

    open(OUT,">$out") || die "can't write to $out";

    my ($rank,$rank2,$score,$offset,$oldsc)=(0,0,0,0,1);

    foreach $docno(sort {$result1{$b}<=>$result1{$a}} keys %result1) {
        $score= sprintf("%.7f",$result1{$docno});
        my ($docno0,$relsc,$rank0,$sc0,$rest)=split(/\s+/,$result0{"$docno"},5);
        $rank++;
        # convert zero/negative score to non-zero value
        if ($score<=0) { $score= sprintf("%.7f",$oldsc-$oldsc*0.1); }
        print OUT "$docno $relsc $rank $score $rest\n";
        $oldsc=$score;
    }

    ($rank,$score,$oldsc)=&rrgrp(\%result2,\%result0,$rank,$score,$oldsc);
    ($rank,$score,$oldsc)=&rrgrp(\%result3,\%result0,$rank,$score,$oldsc);
    ($rank,$score,$oldsc)=&rrgrp(\%result4,\%result0,$rank,$score,$oldsc);
    ($rank,$score,$oldsc)=&rrgrp2(\%result5,\%result0,$rank,$score,$oldsc,\@rest);

    close OUT;

} #endsub rerank1


sub rrgrp {
    my($rhp,$r0hp,$rank,$score,$oldsc)=@_;

    my $rank2=1;
    my $offset=0;
    foreach my $docno(sort {$rhp->{$b}<=>$rhp->{$a}} keys %$rhp) {
        # offset: to ensure correct sorting/ranking for the whole result
        if ($rank2==1 && $rhp->{$docno}>$score) {
            $score -= $score*0.1;
            $offset= $score/$rhp->{$docno};
            print STDOUT "$docno: sc1=$rhp->{$docno}, sc2=$score, off=$offset\n" if ($debug);
        }
        if ($offset) { $score= sprintf("%.7f",$rhp->{$docno}*$offset); }
        else { $score= sprintf("%.7f",$rhp->{$docno}); }
        my ($docno0,$relsc,$rank0,$sc0,$rest)=split(/\s+/,$r0hp->{"$docno"},5);
        $rank++;
        # convert zero/negative score to non-zero value
        if ($score<=0) { $score= sprintf("%.7f",$oldsc-$oldsc*0.1); }
        print OUT "$docno $relsc $rank $score $rest\n";
        $rank2++;
        $oldsc=$score;
    }

    return($rank,$score,$oldsc);

} #endsub rrgrp


sub rrgrp2 {
    my($rhp,$r0hp,$rank,$score,$oldsc,$lp)=@_;

    my $rank2=1;
    my $offset=0;
    foreach my $docno(@$lp) {
        # offset: to ensure correct sorting/ranking for the whole result
        if ($rank2==1 && $rhp->{$docno}>$score) {
            $score -= $score*0.1;
            $offset= $score/$rhp->{$docno};
            print STDOUT "$docno: sc1=$rhp->{$docno}, sc2=$score, off=$offset\n" if ($debug);
        }
        if ($offset) { $score= sprintf("%.7f",$rhp->{$docno}*$offset); }
        else { $score= sprintf("%.7f",$rhp->{$docno}); }
        my ($docno0,$relsc,$rank0,$sc0,$rest)=split(/\s+/,$r0hp->{"$docno"},5);
        $rank++;
        # convert zero/negative score to non-zero value
        if ($score<=0) { $score= sprintf("%.7f",$oldsc-$oldsc*0.1); }
        print OUT "$docno $relsc $rank $score $rest\n";
        $rank2++;
        $oldsc=$score;
    }

    return($rank,$score,$oldsc);

} #endsub rrgrp


#---------------------------------------------
# compute eval stat from result file
#---------------------------------------------
#  arg1= query number
#  arg2= pointer to result file
#  r.v.= eval stat hash
#        $hash{$name}=$val
#---------------------------------------------
sub evalstat {
    my($qn,$rtf)=@_;
    
    my ($relnT,$relnO)=(0,0);
    my (%P,%R,%eval)=();
    
    open(IN,$rtf) || die "can't read $rtf";
    my @lines=<IN>;
    close IN;
    
    my $rank2=0;
    foreach (@lines) {
    
        $rank2++;
        
        s/^\s+//;
        my ($dn,$rel)=split/\s+/;

        if ($rel) {
            $relnT++;
            $relnO++ if ($rel>1);
        }

        my $Pt=sprintf("%.4f",$relnT/$rank2);
        my $Rt=sprintf("%.4f",$relnT/$qrelcnt{$qn}{'topic'});
        $P{$rank2}{'topic'}=$Pt;
        $R{$rank2}{'topic'}=$Rt;

        my $Po=sprintf("%.4f",$relnO/$rank2);
        my $Ro=sprintf("%.4f",$relnO/$qrelcnt{$qn}{'opinion'});
        $P{$rank2}{'opinion'}=$Po;
        $R{$rank2}{'opinion'}=$Ro;

        if ($rel) {
            $eval{'apT'} += $Pt;
            $eval{'apO'} += $Po if ($rel>1);
        }

    }

    $eval{'apT'}= sprintf("%.4f",$eval{'apT'}/$qrelcnt{$qn}{'topic'});
    $eval{'rpT'}= $P{$qrelcnt{$qn}{'topic'}}{'topic'};

    $eval{'apO'}= sprintf("%.4f",$eval{'apO'}/$qrelcnt{$qn}{'opinion'});
    $eval{'rpO'}= $P{$qrelcnt{$qn}{'opinion'}}{'opinion'};

    foreach $rnk(10,50,100) {
        my $rnkT= "p$rnk"."T";
        my $rnkO= "p$rnk"."O";
        $eval{$rnkT}= $P{$rnk}{'topic'};
        $eval{$rnkO}= $P{$rnk}{'opinion'};
    }

    return (%eval);

} #endsub evalstat


AUTOLOAD {
    print "$AUTOLOAD to be coded<p>";
}

