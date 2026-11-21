---
lang: en
title: Lecture 3
permalink: /bf.msu.2026/lecture3/
---
# Lecture 3. From reads to a count matrix: alignment and quantification

This lecture starts the computational part of the course: how sequencing reads become a **count matrix** — genes × samples (or genes × cells), with an expression value in each entry. Almost everything later in the course works with such matrices, so from here on we mostly stop thinking about sequences.

Throughout, we assume a well-studied organism with a reference genome and gene annotation. Assembling and annotating genomes is a separate field; its hard cases are polyploid plants, heavily duplicated genomes and unusual species, not human or mouse.

The explanations below are given for bulk RNA-seq; single-cell data fit the same scheme, and Section 13 lists the differences.

**The big picture.** The sequencer gives you FASTQ files (for paired-end data, one file with forward and one with reverse reads). A 150-nt read usually occurs only once in the transcriptome or genome (paralogs aside). So in principle quantification is simple: find where each read comes from, and count reads per gene. A naive string search would do this, but it would be far too slow for tens of millions of reads, and it would not handle splicing or alternative splicing. The rest of the lecture is about solving those two problems.

## 1. Read QC: what is specific to RNA-seq

General read quality control (FastQC and similar tools) belongs to an NGS course. In practice, if a library is bad, the sequencing facility usually tells you. A few things look specific to RNA-seq libraries, and some of them look alarming without being a problem.

- **Uneven base composition at the start of reads — expected.** Bulk libraries are usually made with random hexamer priming, and hexamers do not bind equally well. As a result, the first \~10 positions of reads have a skewed base composition. Practically every RNA-seq library shows this “hat” at the start of the per-base content plot. A position where one base reaches \~100%, on the other hand, suggests leftover adapter or index sequence.
- **High sequence duplication — mostly expected.** In RNA-seq a few genes are expressed at very high levels, so many reads are identical for biological reasons. Very high duplication together with strongly skewed content can point to a contaminant that dominates the library, such as rRNA left after poor depletion or mitochondrial RNA.
- **Two peaks in the per-read GC content.** A genome has a fairly characteristic GC content, so a bimodal distribution can mean that material from two species is mixed (contamination).
- **10x libraries.** Standard QC reports make little sense for Read 1. It contains the cell barcode and UMI followed by poly(T). Cell barcodes come from a fixed whitelist designed so that a single sequencing error can be corrected. UMIs are random. Only Read 2 (the cDNA) can be judged with the usual metrics.

## 2. Mapping vs alignment, and why references are indexed

The two words are often used interchangeably, but they describe different procedures.

- **Alignment** in the classical sense finds the best global (Needleman–Wunsch) or local (Smith–Waterman) alignment of two sequences by dynamic programming. It makes no assumption about how similar they are, and it costs O(m·n) for sequences of lengths m and n. One read against a mammalian genome takes seconds. Millions of reads would take on the order of a million seconds — weeks.
- **Mapping** uses the fact that a read is almost identical to some piece of the reference: ideally it is an exact substring. So the problem becomes *finding a substring in a string*, which can be done very fast if the reference is prepared in advance.

**The dictionary analogy.** Finding a word in an unsorted list of words means reading the whole list. In a sorted dictionary, binary search takes about log(N) steps. Read mappers do the same: they build an **index** of the reference — a suffix array, an FM-index (based on the Burrows–Wheeler transform), or similar. With a suffix tree, search time depends only on the length of the read, not of the genome. Suffix trees take too much memory for whole genomes, though, so practical tools use suffix arrays or FM-indexes.

**The trade-off: building the index.** Indexing is often the slowest single step — typically an hour or so, not weeks. But it is done once per genome version and reused for every sample, and pre-built indexes for common organisms can often be downloaded.

## 3. Genome or transcriptome reference; splicing

You can map reads to the **genome** or to a **transcriptome** (the set of annotated transcript sequences).

- A transcriptome is smaller: no intergenic regions and no introns, so mapping is faster if you only care about processed mRNA.
- But it does not remove the problem of **alternative splicing**. Alternative splicing is not a textbook rarity: most multi-exon human genes have several isoforms (open any gene in a genome browser to see this). Isoforms with clearly understood functional differences are the rarer case; many alternative isoforms may simply reflect how short and permissive splice-site signals are.
- If the reference contains isoforms A–B–C and A–C, a read lying entirely in exon A matches both. So with a transcriptome reference you need a strategy for reads that match several transcripts (Sections 11–12).

Whatever the reference, an RNA-seq aligner must handle splicing: a read can span an exon–exon junction, which in the genome looks like a large gap. This is the main difference from DNA aligners, which do not expect large gaps. That is why RNA-seq uses different tools: today mainly **STAR** and **HISAT2** for alignment, and **kallisto** or **salmon** for pseudoalignment (Section 12). Older tools such as TopHat are no longer used.

## 4. How spliced aligners work (STAR, HISAT2)

**STAR** (2013) is still the most widely used RNA-seq aligner. It works well with default settings, but it needs a lot of RAM (about 30 GB for a human genome). **HISAT2** gives very similar results, is faster and needs much less memory. **kallisto** (2016) is faster still and runs even on a laptop.

**STAR's two-step search.**

1. **Seed search.** STAR searches the genome's suffix array for the *maximal mappable prefix*: the longest part of the read, starting from its first base, that matches the genome exactly.
2. **Next seed.** It then searches again starting from the first unmatched base. If a read spans a splice junction, the two seeds land in two exons, with the intron between them.
3. **Stitching and extension.** The seeds are stitched and extended with local dynamic-programming alignment. This step tolerates mismatches and indels, and gives the alignment a score. Poorly matching read ends can be left unaligned (soft-clipped, Section 6).

**Annotation helps.** When building a STAR index you usually supply both the genome and a gene annotation (GTF). STAR then knows the annotated splice junctions and favours alignments that use them. HISAT2 can also be given known splice sites. Both tools can discover **novel junctions**, but these must pass stricter filters: canonical splice motifs and support from several reads. An annotated junction is accepted with a single read.

**Mismatches and the seed-length trade-off.** A few mismatches are not a problem, as long as an exact seed can still be found; most reads differ from the reference by zero or one base. Problems start when too many positions differ:

- **Mapping to the wrong species.** Rodents, for example, evolve fast, and the long branches on their phylogenetic tree mean many substitutions per site.
- **Bisulfite sequencing.** Unmethylated cytosines are converted to uracil and read as T, while methylated cytosines stay C. Most cytosines in the genome are unmethylated, so many positions differ from the reference. Bisulfite reads therefore need specialized aligners (e.g., Bismark) that work on in-silico converted genomes.

Why not use very short seeds to be tolerant of differences? Because short seeds occur everywhere by chance. A 4-nt word has 4⁴ = 256 variants, so in a \~3×10⁹-nt genome each one occurs millions of times, and every such hit would have to be extended. Long seeds are fast but sensitive to differences; short seeds are tolerant but slow.

## 5. Do you need adapter trimming?

NGS courses often say that the first step is always adapter and quality trimming (Cutadapt, Trim Galore and similar). For de novo genome or transcriptome assembly this is indeed important. For mapping RNA-seq reads it is usually unnecessary; to see why, start with where adapter sequence ends up in a read.

**Where adapters appear.** When the insert is shorter than the read, the sequencer reads through the insert into the adapter on the other side. So adapter sequence appears at the **3′ end** of the read, not at its start.

For RNA-seq mapping, trimming is largely optional. STAR, HISAT2 and BWA-MEM align reads locally and simply **soft-clip** ends that don't match. kallisto skips k-mers that don't match. (Bowtie2 in its default end-to-end mode is an exception.) Trimming may let a fraction of a percent more reads align. If your conclusions depend on a couple of percent of reads, they are probably unstable anyway. Trimming matters more in special protocols with many expected differences from the reference, such as bisulfite sequencing, where it is better not to make the aligner's job harder.

## 6. SAM/BAM: storing alignments

Storing each read as a gapped alignment against a whole chromosome (as in FASTA alignments) would be absurdly wasteful. Instead, the **SAM** format stores for each read:

- the read's own sequence (SEQ) and base qualities (QUAL);
- the reference sequence name (RNAME, e.g., chr1) and the leftmost position where the alignment starts (POS);
- a **CIGAR** string describing how the read lines up with the reference from that position;
- **MAPQ**, flags (paired, reverse strand, unmapped, secondary…) and optional tags.

**BAM** is the binary, compressed version of SAM, with the same content.

**CIGAR operations.**

| Op | Meaning |
| --- | --- |
| M | Alignment match — the bases are aligned, which can be a match *or* a mismatch |
| I / D | Insertion in the read / deletion from the read relative to the reference |
| **N** | Skipped region of the reference — in RNA-seq, an **intron** in a spliced read |
| S | Soft clip — bases kept in SEQ but not aligned |
| H | Hard clip — bases removed from SEQ |
| = / X | Explicit sequence match / mismatch (optional alternative to M) |

Example: `30M2000N70M` = 30 aligned bases, a 2,000-nt intron, then 70 aligned bases. Mismatches inside M blocks are recorded in tags (NM = edit distance, MD = which bases differ).

**MAPQ** is not a measure of how well the read matches. It measures how confident the aligner is that the read is placed in the *right location*: MAPQ = −10·log₁₀ P(wrong position). A read that matches perfectly but equally well in two places gets a low MAPQ. STAR uses only a few values: 255 = unique, 3 = two loci, 1 = three or four, 0 = more than four.

**Soft rather than hard clipping.** With soft clipping, a BAM file keeps the full read sequence and its base qualities. If it also contains the unmapped reads, the original FASTQ can be fully reconstructed from it, which has rescued more than one project whose FASTQ files were lost. Note that STAR does not write unmapped reads to the BAM by default (`--outSAMunmapped Within` enables this). This is also why the SRA accepts BAM submissions that include unmapped reads.

**Viewing alignments.** A BAM records how each read differs from the reference, not the reference itself. Genome browsers such as IGV therefore always load two files: the BAM (with its index) and the reference genome.

## 7. Novel junctions and variant calling from RNA-seq

**Finding novel splice isoforms: two-pass mapping.** Annotated junctions are accepted with little evidence, novel ones need more. To study alternative splicing you can map twice:

1. Map all samples and collect junctions detected with reasonable support, building a draft set of novel junctions.
2. Re-map with these junctions added as if they were annotated (STAR supports this as `--twopassMode Basic`).

The second pass is more sensitive to reads that cross the new junctions with short overhangs.

**Variant (SNP) calling from RNA-seq: avoid it when you can.**

- **Coverage is extremely uneven.** Gene expression levels differ by thousands of times, so many positions have almost no reads.
- **Allelic expression is not balanced.** The maternal and paternal alleles need not be expressed equally (allele-specific expression, imprinting, X inactivation).
- **RNA-specific artifacts.** RNA editing (A-to-I) and misalignments near splice junctions look like variants.

Whole-exome sequencing is now cheap per sample, so if you need variants, sequence DNA. RNA-based calling is a last resort.

## 8. Alignment QC

Read-level QC usually belongs to the facility, but checking the alignment is your job. The aligner's summary and tools such as RSeQC or Qualimap give the main metrics.

**Mapping rate.** This is the first and most important number. For a good human or mouse library, typically 70–90% of reads map, most of them uniquely. A much lower rate suggests:

- **The wrong reference.** For example, a different but related species: reads from one *Mus* species against the house-mouse genome map noticeably worse, and mouse reads against rat map much worse still.
- **Contamination**, such as a mixture of species.
- **A poor library**, such as adapter dimers, rRNA, or genomic DNA.

**Where reads land.** In a typical gene (TSS → 5′ UTR → coding exons with introns → 3′ UTR → TES), most reads in a poly(A) library should fall in exons and UTRs — usually more than half. Fewer should fall in introns, and few in intergenic regions. Intergenic reads come from unannotated genes (especially lncRNAs), noisy transcription initiation, and genomic DNA contamination.

**Why so many intronic reads?** Introns are much longer than exons, so if libraries contained a lot of unspliced RNA, intronic reads would dominate. With poly(A) selection they are a minority — but often still 10–30%. Part of this comes from pre-mRNA that was polyadenylated before splicing finished. Much of the rest comes from **internal priming**. Introns are long and under weak selection, so they contain many A-rich stretches, and oligo-dT binds to them. In data these show up as intronic coverage peaks right next to A-rich motifs, as shown by the authors of **RNA velocity**. That method then uses the ratio of unspliced (intronic) to spliced reads per gene to infer whether a gene is being switched on or off. Intronic reads are therefore not just noise.

**Clipping profile.** This shows at which read positions the aligner soft-clipped bases. Clipping at the 3′ end is expected (adapter read-through, falling base quality). Clipping in the first few bases is also common in random-primed libraries. Random hexamers can prime with mismatches, so the bases copied from the primer may not match the RNA; mispriming errors concentrate in the first \~7 nt of the cDNA. Clipping starting in the middle of reads is a warning sign, e.g., of a problem with insert size during library preparation.

**Gene body coverage.** This shows how evenly reads cover genes from 5′ to 3′ (Lecture 1: 3′ bias signals degradation in poly(A) libraries).

## 9. Counting reads per gene; overlaps and multimapping

In the simplest case, quantification just counts reads that fall into each gene. Tools: **featureCounts** (very fast) or **htseq-count**, given a BAM and the annotation (GTF). STAR can output the same gene counts directly (`--quantMode GeneCounts`). The result for one sample is a vector of counts per gene; for many samples, a matrix.

The hard cases are reads that could belong to more than one gene.

**Overlapping genes.** Genes can overlap, on the same or on opposite strands (Lecture 1: \~19% of human genes overlap a gene on the other strand). Stranded libraries resolve opposite-strand overlaps. For the rest, counting tools let you choose a rule: discard ambiguous reads, or assign them by overlap.

**Multimapping reads.** These reads align equally well to several places. By default they are excluded from gene counts, because you can't tell which gene they came from. Multimapping is not random: it hits particular gene families systematically, so excluding multimappers biases those genes.

- **Ribosomal DNA.** rRNA genes are present in hundreds of copies, organized in tandem arrays at the nucleolus organizer regions (in humans, on the short arms of the five acrocentric chromosome pairs). These arrays were largely missing from standard reference assemblies before telomere-to-telomere genomes; only fragments are present, partly masked. One way to work with rRNA reads is to mask rDNA-like sequence in the genome (e.g., found by BLAST of a reference rDNA unit), then add a single complete rDNA unit as a separate contig.
- **Recent paralogs.** Duplicated genes can be nearly identical. A classic example is the primate long- and middle-wavelength cone opsins (*OPN1LW*, *OPN1MW*). Reads from the shared regions multimap and are dropped, so these genes' expression is underestimated.

## 10. Gene length and isoforms

**Reads depend on length.** In full-length protocols (standard bulk RNA-seq, Smart-seq) a transcript is fragmented along its whole length. So a long transcript yields more reads than a short one present at the same number of molecules. Equal read counts for two genes do not mean equal numbers of molecules. This is why bulk analyses use length-aware measures such as TPM.

**Isoforms make "gene length" variable.** Different isoforms of one gene can have different lengths, for example the same coding sequence with UTRs of different lengths. Such isoforms make the same protein. Now imagine tissue A uses a long-UTR isoform and tissue B a short one, with the same number of molecules. Raw gene-level read counts will be higher in A purely because of length. Gene-level length normalization with a single fixed gene length won't fix this either, because the effective length differs between tissues. You can see the difference by eye in a genome browser, but simple gene-level counting can't separate it from a real change in expression.

- **Example: UTR variation.** *MS4A1* (CD20, a B-cell surface marker and a therapeutic target) has isoforms that differ mainly in their UTRs.
- **Example: functional isoforms.** *PTPRC* (CD45) has isoforms that differ in alternative exons and in glycosylation: CD45RA is typical of naive T cells, CD45RO of memory and effector T cells. The switch happens on activation, typically in lymph nodes or tertiary lymphoid structures. Here the isoform itself carries biological information.
- **A naming tip.** For most genes, the mouse ortholog has the same name with only the first letter capitalized (*PTPRC* → *Ptprc*).

**The working assumption.** Most analyses stay at the gene level and assume that **isoform usage does not change between the conditions being compared** (disease vs healthy, treated vs untreated, day 1 vs day 2). Then a two-fold change in gene counts reflects a two-fold change in expression. This holds for most genes, but not all.

- **Alternative polyadenylation** — the choice between several transcription end sites — can differ systematically between tissues and states. For example, proliferating cells tend to use shorter 3′ UTRs.
- **Studying alternative splicing itself** requires isoform-level quantification.

A side remark: "is gene X expressed in this tissue?" is rarely a meaningful question on its own. Expression is a distribution, not a yes/no; what can be meaningfully answered is how expression differs between conditions.

## 11. Isoform quantification with expectation–maximization (EM)

**Expectation–maximization** is a general algorithm for maximum-likelihood estimation when some information is hidden. A familiar use is fitting a mixture of two Gaussians: guess the two components, assign each point to them probabilistically, re-estimate the components, and repeat until nothing changes. It is similar in spirit to k-means.

For isoforms, the hidden information is which isoform each ambiguous read came from.

1. **Initialize.** Start with a guess about isoform proportions, e.g., 50:50.
2. **E-step.** Reads compatible with only one isoform count fully toward it. Reads compatible with several isoforms are split fractionally in proportion to the current estimates (and isoform lengths): with 50:50, each ambiguous read gives 0.5 to each isoform.
3. **M-step.** Re-estimate the isoform proportions from these (now fractional) counts. The uniquely assigned reads pull the estimate away from 50:50.
4. **Repeat** until the estimates converge, usually within tens of iterations.

The outputs are *estimated* counts per isoform, which can be non-integer, and length-normalized abundances (TPM). Summing isoform abundances per gene gives gene-level values that account for isoform usage. Uncertainty in these estimates is assessed separately, for example by bootstrapping.

The same logic works for reads shared between **different genes** — e.g., recent paralogs. If gene 1 is clearly more highly expressed than gene 2 (judging from reads unique to each), an ambiguous read is more likely to come from gene 1 and is assigned mostly there, instead of being discarded.

## 12. Pseudoalignment: kallisto and salmon

For most experiments the alignment itself is never looked at; what you need is the count matrix. Pseudoalignment skips the base-by-base alignment and goes straight to quantification.

**How kallisto works.**

1. **Index the transcriptome**, not the genome. kallisto builds a k-mer index (k = 31) of all annotated transcripts.
2. **Pseudoalign each read.** kallisto looks up the read's k-mers and finds the set of transcripts **compatible** with all of them. It does not determine the exact position or base-level alignment — hence "pseudo". No splicing search is needed, because transcripts are already spliced.
3. **Group reads into equivalence classes**: reads compatible with the same set of transcripts.
4. **Run EM** (Section 11) over transcripts to estimate their abundances. kallisto doesn't care whether compatible transcripts belong to one gene or to different genes. Gene-level values are obtained afterwards by summing transcripts.

The data structure (a transcriptome de Bruijn graph) is often emphasized in explanations. It is an implementation detail of the index; the core of the method is compatibility plus EM.

**salmon** follows the same logic with a different index and selective alignment, and adds bias corrections. Its results are very highly correlated with kallisto's.

**Pros:**

- Very fast and light on memory: it runs on a laptop or in Google Colab, even on full public datasets. (It has even been demonstrated on a handheld game console.)
- Gives transcript-level estimates directly.

**Cons:**

- No regular BAM, so no variant calling.
- It can only quantify transcripts that are in the reference, so it cannot discover novel isoforms or junctions.

## 13. Processing single-cell data

**Smart-seq.** Each cell is a separate sample with its own FASTQ files, so everything above applies directly: run STAR or kallisto per cell. Smart-seq is full-length and has no UMIs, so length dependence and isoform effects apply just as in bulk.

**10x Chromium.** Read 1 holds the cell barcode and UMI; Read 2 holds the cDNA. Processing therefore:

1. aligns Read 2 to the genome;
2. assigns each read to a cell by its barcode, correcting single-base errors against the barcode whitelist;
3. collapses reads with the same cell barcode, gene and UMI into one molecule. UMIs that differ by one base from a more abundant UMI are usually merged as sequencing errors.

The output is a **genes × cells matrix of UMI counts**.

**Cell Ranger** (from 10x) does all of this in one command. You provide a reference (pre-built ones can be downloaded) and the FASTQ files. Cell Ranger detects the chemistry version automatically, maps Read 2 with STAR, counts UMIs per gene and produces a detailed HTML report. **kallisto | bustools** (the `kb` tool, from Lior Pachter's lab at Caltech) does the same with pseudoalignment. It is much faster and lighter, and nowadays similarly easy to run: you name the chemistry (e.g., 10xv3) instead of specifying barcode and UMI positions. Its reports are less polished.

**Why no length normalization for 10x.** Two things together make each original mRNA molecule contribute one count, whatever its length or isoform. Only the barcoded 3′ fragment of each cDNA is sequenced, and UMIs collapse all PCR copies of a molecule. So the isoform-length problem from Section 10 largely disappears. Isoform-level quantification is not possible anyway, since only the 3′ end is read.

**A caveat with paralogs.** Cell Ranger discards reads that map to multiple genes. This matters for recently duplicated genes. In retina data, for example, cone photoreceptors express nearly identical opsin paralogs, and kallisto | bustools separated two cone subpopulations somewhat better than Cell Ranger. The reason is that EM-based assignment kept reads from the shared regions of the paralogous genes instead of discarding them.

## 14. Key points and glossary

1. The goal of preprocessing is a count matrix; after that, the course works with matrices, not sequences.
2. Read mappers are fast because they index the reference once (suffix arrays, FM-index) and then look up exact seeds. RNA-seq aligners must also handle splicing.
3. STAR and HISAT2 align spliced reads using exact seeds plus local extension. Known junctions need less evidence than novel ones. Two-pass mapping helps find novel junctions.
4. Adapter trimming is largely optional for RNA-seq mapping, because aligners soft-clip unmatched ends.
5. In SAM/BAM, CIGAR "N" marks introns, "S" soft clips; MAPQ measures confidence in the position, not match quality.
6. Check mapping rate, read distribution (exons, introns, intergenic), clipping profile and gene body coverage. Intronic reads are partly informative (internal priming, RNA velocity).
7. Multimapping reads are usually discarded, which systematically underestimates repeated genes and recent paralogs. EM-based tools redistribute them instead.
8. In full-length data, read counts depend on transcript length, and gene-level analysis assumes stable isoform usage. 10x UMI counts are length-independent.
9. kallisto/salmon pseudoalign to a transcriptome and use EM: fast, transcript-level, but no BAM and no novel isoforms. For 10x, use Cell Ranger or kallisto | bustools.

| Term | Meaning |
| --- | --- |
| Count matrix | Genes × samples (or cells) table of expression counts |
| Mapping / alignment | Finding a read's location via an index / finding the optimal base-level alignment by dynamic programming |
| Index (suffix array, FM-index) | Pre-processed reference that allows fast substring search |
| Seed (MMP) | Exactly matching piece of a read used to anchor its alignment |
| Splice junction | Exon–exon boundary; a gap (CIGAR "N") in a genome alignment |
| Two-pass mapping | Re-mapping with junctions discovered in a first pass |
| SAM / BAM | Text / binary format for alignments |
| CIGAR | String describing how a read aligns (M, I, D, N, S, H) |
| MAPQ | Confidence that the read is placed at the correct location |
| Soft / hard clipping | Unaligned read ends kept / removed in the stored sequence |
| Multimapping read | Read aligning equally well to several locations |
| TPM | Transcripts per million: length- and depth-normalized abundance |
| Expectation–maximization | Iterative estimation used to assign ambiguous reads to isoforms or genes |
| Pseudoalignment | Determining which transcripts a read is compatible with, without base-level alignment |
| Equivalence class | Group of reads compatible with the same set of transcripts |
| Internal priming | Oligo-dT binding to A-rich stretches inside transcripts, often in introns |

## Further reading

- [Dobin et al., 2013 — STAR: ultrafast universal RNA-seq aligner](https://doi.org/10.1093/bioinformatics/bts635)
- [Bray et al., 2016 — Near-optimal probabilistic RNA-seq quantification (kallisto)](https://doi.org/10.1038/nbt.3519)
- [Hansen et al., 2010 — biases caused by random hexamer priming](https://pubmed.ncbi.nlm.nih.gov/20395217/)
- [van Gurp et al., 2013 — consistent errors due to random hexamer mispriming](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3875578/)
- [La Manno et al., 2018 — RNA velocity of single cells](https://doi.org/10.1038/s41586-018-0414-6)
- [SAM format specification](https://samtools.github.io/hts-specs/SAMv1.pdf)
