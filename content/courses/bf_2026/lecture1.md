---
lang: en
title: Lecture 1
permalink: /bf.msu.2026/lecture1/
---
# Lecture 1. Transcriptomics, Illumina sequencing and bulk RNA-seq library preparation

This is the first lecture of the single-cell transcriptomics course. It covers what RNA-seq measures, how Illumina sequencing works, and how a bulk RNA-seq library is made from tissue. Single-cell library preparation is the topic of Lecture 2; data analysis starts in Lecture 3.

## 1. What transcriptomics is

The word "transcriptomics" is used in two senses; this course is about the second one.

1. **Which transcripts an organism has.** The goal is to learn RNA sequences, assemble a transcriptome, find genes, proteins and homologs. This is how poorly studied organisms without a good reference genome are approached.
2. **How strongly each gene is expressed.** The genes are already known (for humans there is a telomere-to-telomere genome assembly), and the question is which of them are active in a given tissue and at what level. When people say "transcriptomics" without qualification, they usually mean this.

**Example of the first kind — the supergroup Provora** (Nature, 2022; authors include K. Mikhailov and V. Aleoshin, Belozersky Institute, Moscow State University). The authors sequenced transcriptomes of poorly characterized single-celled eukaryotes. Phylogenetic analysis showed they form a separate clade, distant from known groups. Such protists are hard to grow in large numbers, so very sensitive methods are needed, down to single-cell transcriptomics.

Transcriptome assembly and assessment of its completeness (BUSCO and similar tools) are outside the scope of this course.

## 2. Why we measure RNA rather than protein

Most often what we really care about is protein levels, but we measure RNA because it is cheaper and far more sensitive. This section explains why expression is worth measuring at all, why RNA is used instead of protein, and how far RNA can be trusted as a proxy.

**Why expression matters at all.** Knowing which genes are active helps to understand how diseases develop, find therapeutic targets and characterize unknown cell populations. A clinical example is immunohistochemical staining for PD-L1 in non-small cell lung cancer. In patients without targetable driver mutations, high PD-L1 often means first-line monotherapy with a PD-1/PD-L1 inhibitor. With low PD-L1, immunotherapy is usually combined with chemotherapy. When a driver mutation is present (EGFR, ALK and others), targeted therapy comes first.

**Why not protein mass spectrometry.** The issue is less accuracy than sensitivity. Unlike nucleic acids, proteins cannot be amplified, so mass spectrometry needs more input, measurements are noisier and fewer proteins are covered. In practice, in proteomics and metabolomics you may expect hundreds of proteins to change, yet only a handful reach statistical significance.

**How well RNA predicts protein.** Using RNA as a proxy assumes that RNA and protein levels are correlated. This is only partly true, and it depends on what exactly is compared.

- **Across genes within one tissue.** Take one tissue (e.g., brain) and, for every gene, compare its RNA level with its protein level. The correlation is clear but far from perfect. (Such plots contain thousands of overlapping points, so they are best drawn as 2D histograms, where colour shows point density.)
- **For one gene across tissues.** Now take a single gene, measure it in several tissues (e.g., 8) and correlate its RNA and protein levels across them; repeat for every gene. The median correlation is only about 0.35, with a wide spread: some genes correlate strongly, others are close to zero.
- **Why some genes show near-zero correlation.** These are often housekeeping genes with nearly constant expression. If a feature barely changes between tissues, only noise remains, and two independent noises are uncorrelated. Genes that differ strongly between tissues correlate much better.

**RNA and protein are shifted in time.** Protein accumulates with a delay of the order of hours after the RNA.

- In slow processes (many tumours develop over years) the state can be treated as roughly steady.
- In fast processes the delay is critical. In mouse embryos the morphology changes within a day (around E8–E9: neural tube closure, neural crest migration), so 6 hours is a lot.
- A practical trap: embryos in one litter are not fertilized at exactly the same time and can differ in stage by up to half a day. A perturbation (any intervention: a compound, a knockout, a knockdown) applied "at E7" may in fact hit different stages.

There are also questions where RNA itself is the target: non-coding RNAs, transcription and post-transcriptional regulation. Then RNA-seq answers the question directly.

## 3. Old-generation vs next-generation sequencing

To measure RNA at scale, we convert it to DNA and sequence it. Before looking at how this is done, it helps to place modern sequencing in context. The key difference between the two generations is parallelism: NGS reads millions to billions of different molecules at once, Sanger sequencing reads one target per reaction. "Next generation" has long stopped being new, but the term stuck.

|  | Sanger (old generation) | NGS (Illumina and others) |
| --- | --- | --- |
| Molecules per run | One target per reaction | Millions to billions of fragments |
| Typical tasks | Checking a plasmid before cloning, testing for a mutation in one known gene | Open-ended questions: whole genomes, transcriptomes, ChIP-seq |
| When to choose | A clear hypothesis about a specific region | You want as much data as possible without a prior hypothesis |

"Old" does not mean "worse": for targeted tasks Sanger is cheaper and still the standard.

## 4. How Illumina sequencing works

An Illumina sequencer is essentially a fluorescence microscope with microfluidics: on every cycle it photographs which base was added in each of millions of clusters. Below is a simplified scheme; modern instruments (NovaSeq) use more complex flow cells and amplification, but the logic is the same.

### 4.1. Flow cell and library

- **Flow cell** — a glass slide with channels called lanes: 1, 2, 4 or 8 depending on the type. The surface of each lane is coated with oligonucleotides of two known sequences (P5 and P7). This is why flow cells are expensive.
- It is called a *flow* cell because a series of reagents constantly flows through it.
- **Library** — a mixture of **DNA** molecules (not RNA) with a common architecture: the insert you want to read in the middle (a genome fragment, cDNA, a ChIP-seq region), technical sequences at both ends.
- Each technical end consists of three parts: a region complementary to the flow-cell oligos (P5/P7), an **index** (i5/i7), and a binding site for the sequencing primer.

### 4.2. Bridge amplification: from one molecule to a cluster

1. Single-stranded library molecules hybridize to the flow-cell oligos by either end. The concentration is chosen so that molecules land sparsely — ideally one per spot.
2. The flow-cell oligo acts as a primer; polymerase synthesizes the complementary strand, which is now **covalently attached** to the flow cell.
3. The free end of the strand bends over and hybridizes to a neighbouring oligo, forming a "bridge", and synthesis continues from it.
4. After tens of cycles a **cluster** forms around the original molecule — thousands of its copies. The copies cannot drift away because all of them are attached to the surface.

**Why a cluster is needed.** The signal from a single fluorophore is too weak for the Illumina detector. Thousands of identical copies lighting up in the same colour at the same spot give a readable signal. The alternative — detectors sensitive enough for single molecules, as in PacBio — is a different approach at a different cost.

### 4.3. Linearization

After amplification a cluster contains both strands (forward and reverse), but only one orientation can be read at a time. One of the two flow-cell oligo types carries a modified nucleotide. It is cleaved specifically (enzymatically or chemically), and all strands attached through it are washed away. An ordinary restriction enzyme would not work here: the molecules are single-stranded and their insert sequences differ. The flow cell is then washed free of leftover reagents.

### 4.4. Sequencing by synthesis (SBS) with reversible terminators

Each base of a read is a separate cycle of four steps:

1. **Incorporate.** A sequencing primer binds the molecule. Polymerase and nucleotides carrying a fluorophore and a **reversible terminator** are added: exactly one base is incorporated, and synthesis cannot continue.
2. **Wash.** Unincorporated labelled nucleotides are removed, otherwise everything would glow.
3. **Image.** A laser excites the fluorophores, and a camera records the colour of each cluster.
4. **Cleave** the terminator and fluorophore chemically, then move on to the next cycle.

The number of cycles is set at the start of the run; it determines read length and run time.

How bases are encoded depends on the instrument. Older systems (HiSeq 2500, the original MiSeq) use four dyes, one per base. NovaSeq, NextSeq and MiSeq i100 use **two-channel** chemistry: one base lights up in both channels, two bases in one channel each, and G is dark. As a result, an empty or failed cluster is read as G, which produces artificial poly-G tails in reads that should be trimmed.

### 4.5. From images to files

- The raw data are images from every cycle, hundreds of gigabytes. They are processed on the instrument and usually not stored.
- **Base calling** converts intensities into bases and quality scores. The output is **BCL files** (base call): binary, organized by cycle, not yet reads.
- Conversion BCL → **FASTQ** (bcl2fastq / BCL Convert) assembles reads and at the same time performs **demultiplexing** by index (Section 5). FASTQ is what you will work with.
- Each lane produces its own set of FASTQ files. So a facility may give you, for example, 4 R1 files and 4 R2 files per sample. These are not technical replicates but different lanes; they are almost always simply merged.

| Flow cell (examples) | Lanes |
| --- | --- |
| MiSeq | 1 |
| NovaSeq 6000 SP / S1 / S2 | 2 |
| NovaSeq 6000 S4, NextSeq 500/550 | 4 |
| HiSeq (high output), NovaSeq X 10B / 25B | 8 |

## 5. Indexes and multiplexing

Indexes make it possible to sequence many libraries on one flow cell and then assign each read to its sample.

**Why.** One Illumina run yields hundreds of millions to billions of reads, while a single sample usually needs far fewer. So libraries from different experiments and labs are pooled and sequenced together.

**How.** An index is a short sequence (usually 8–10 nucleotides) added during library preparation. The P5/P7 adapters are identical for all libraries, while the index is unique to each library. Indexes are read in separate phases of the run, each from its own primer.

**Read order in a paired-end run:**

1. **Read 1 (R1)** — the insert from one end.
2. **Index 1 (I1, i7)** — from the same strand, with a new primer.
3. **Turnaround.** Another round of bridge synthesis regenerates the second strand; **Index 2 (I2, i5)** is read at this stage. Strands attached through the other oligo are then cleaved off.
4. **Read 2 (R2)** — the insert from the opposite end.

In total, the facility has four data streams: R1, R2, I1, I2. You normally receive only R1/R2: after demultiplexing all of your reads carry the same indexes, so I1/I2 files add nothing. If you do receive I1/I2 files, these are the indexes.

### Index hopping and unique dual indexes (UDI)

**Index hopping** means that some reads end up with another library's index and are assigned to the wrong sample. The main cause is free (unligated) adapters and primers in the pooled library: they prime other library molecules and extend them with their own index. It is most noticeable on patterned flow cells with ExAmp amplification (HiSeq 4000/X, NovaSeq). According to Illumina, typical rates are 0.1–2%.

**When it matters.** For expression this fraction is usually lost in the noise; for detecting rare variants it is not. Example: patient A's biopsy has 20% purity (fraction of tumour cells) and a heterozygous mutation, so only \~10% of reads carry it. Sample B, sequenced in the same pool, has 100% purity and a different homozygous mutation. Hopped reads from B can create a false mutation in A at a frequency comparable to real ones.

**Two ways to use two indexes.** *Combinatorial* dual indexing was introduced to increase the number of samples per run: e.g., 12 i7 × 8 i5 = 96 combinations. It does not protect against hopping, because a hopped read often lands on another valid combination. *Unique dual indexes (UDI)* give each library its own i7 **and** i5, neither of which is reused by any other library in the pool. A read is assigned to a sample only if both indexes match; an unexpected pair is discarded. For a read to land in the wrong sample, both indexes would have to hop in a coordinated way, which is orders of magnitude rarer. UDIs became the recommended practice after patterned flow cells appeared (\~2017).

## 6. Read length and paired-end sequencing

Illumina reads are short — typically 2×150 nucleotides on NovaSeq (up to 2×250 on some flow cells) and up to 2×300 on MiSeq. Base quality drops toward the end of a read.

**Why reads can't be longer (phasing).** On every cycle, in a small fraction of molecules in a cluster a base fails to incorporate, and these molecules fall one position behind (phasing). Sometimes the terminator fails and a molecule jumps ahead (pre-phasing). Errors accumulate: the cluster no longer lights up in a single colour, and the signal becomes a mixture. Washing is also imperfect, so background builds up on the flow cell. That is why the base caller's confidence decreases with read length.

**Why read a molecule from both ends (paired-end):**

- **Insert longer than two reads.** We don't know the middle, but we know that the two ends came from one molecule at a known distance. This improves mapping in repeats, helps link exons and detect structural variants and fusions.
- **Insert shorter than two reads.** R1 and R2 overlap: the low-quality end of one read falls on the high-quality start of the other, and the sequence can be corrected.

## 7. Bulk RNA-seq library preparation: the roadmap

The goal is to turn RNA from tissue into short DNA molecules with Illumina adapters while preserving the relative abundance of transcripts. *Bulk* means RNA is extracted from a whole piece of tissue, not from individual cells.

1. **Sample storage**, **total RNA extraction** and integrity check.
2. **Selecting the transcripts of interest**: poly(A) selection or rRNA depletion.
3. **Fragmentation** — before or after reverse transcription, depending on the protocol.
4. **Reverse transcription** (RNA → cDNA) and **second-strand synthesis** (→ double-stranded DNA).
5. **Adapter and index addition**, PCR amplification of the library.
6. **Sequencing.**

This lecture stays at the conceptual level; the technical details of single-cell libraries are covered in Lecture 2.

## 8. Sample storage and RNA quality

RNases are everywhere, so the main goal is to stop degradation quickly. Ideally RNA is extracted straight from fresh tissue, but usually days or weeks pass between surgery and extraction.

| Method | What is done | RNA | Where it is used |
| --- | --- | --- | --- |
| **FFPE** (formalin-fixed paraffin-embedded) | Fixation in formalin, water replaced by paraffin; thin sections are cut from the block and stained (H&E, IHC) | Heavily fragmented and chemically modified; DNA survives better | Histopathology; blocks are kept for decades |
| **Fresh frozen / snap frozen** | Instant freezing in liquid nitrogen (−196 °C), storage at −80 °C | Best quality | Molecular studies, biobanks |
| **RNAlater** | Tissue is submerged in a high-salt stabilizing solution that inactivates RNases | Good, within the storage limits: 1 day at 37 °C, 1 week at 25 °C, 1 month at 4 °C; long term at −20 °C or below | Field work, transport without liquid nitrogen |

**Freeze fast.** Slow freezing forms ice crystals that damage the tissue and the molecules in it.

### RIN — RNA integrity before sequencing

- Total RNA is separated by **length** with capillary electrophoresis (Agilent Bioanalyzer, TapeStation), producing an electropherogram.
- The two main peaks are ribosomal 18S and 28S: rRNA makes up most of total RNA. When RNA degrades, the peaks smear out and the fraction of short fragments grows.
- **RIN (RNA Integrity Number)** ranges from 1 (fully degraded) to 10 (intact); the algorithm is trained on features of the electropherogram. Poly(A) protocols usually require RIN ≥ 7–8.
- For FFPE, RIN is almost always low and uninformative; **DV200** — the fraction of fragments longer than 200 nucleotides — is used instead.

### TIN — integrity estimated from sequenced reads

Bioinformaticians are often not given the RIN, but quality can be estimated from how evenly reads cover genes. **TIN (Transcript Integrity Number**, RSeQC) is computed for each transcript. Often it is enough simply to look at the 5′→3′ gene-body coverage profile.

**Why degradation causes 3′ bias.** In a degraded sample (RNases, heat, formalin) RNA breaks at random positions along its whole length. Poly(A) selection (or reverse transcription primed with oligo-dT) then captures only fragments still attached to the poly(A) tail, i.e. 3′ ends. 5′ pieces separated from the tail are lost. With rRNA depletion and random priming, coverage of degraded RNA stays much more uniform.

- In practice: 3′-biased coverage in a poly(A) library is a typical sign of degradation.
- The exception is protocols where 3′ bias is built in by design (3′-tag methods, most single-cell protocols). There, uneven coverage says nothing about quality.

**About the poly(A) tail.** The tail is not encoded in the genome: the gene contains only a polyadenylation signal, and poly(A) polymerase adds the tail after the pre-mRNA is cleaved. In mammals a newly made tail is about 150–250 nucleotides long and shortens over time.

## 9. Getting rid of ribosomal RNA

Ribosomal RNA is about 80% of total RNA. If it is not removed, most of the sequencing budget goes to useless reads. There are two opposite approaches: pull out what you need, or remove what you don't.

### 9.1. Poly(A) selection (the most common approach)

- mRNAs and many long non-coding RNAs carry a poly(A) tail; rRNA, tRNA and most small RNAs do not. Polyadenylation is mostly a feature of RNA polymerase II transcripts.
- Magnetic beads with attached oligo-dT (particles with a superparamagnetic iron-oxide core) are added to the RNA. Poly(A) tails hybridize to the oligo-dT.
- A magnet holds the beads; the supernatant with rRNA and small RNAs is discarded. The mRNA is then released from the beads by heating.
- Side effect: enrichment for mature mRNA. Polyadenylated molecules are mostly already spliced, so there are fewer intronic reads than with rRNA depletion (where immature pre-mRNA also enters the library).

### 9.2. rRNA depletion (total RNA-seq)

Used when non-polyadenylated RNAs are of interest or when the RNA is degraded.

- **RNase H (e.g., Ribo-Zero Plus).** DNA probes complementary to rRNA form DNA:RNA hybrids with it. RNase H cuts RNA only within such hybrids; DNase then removes the probes. The rest of the RNA is untouched.
- **Capture (original Ribo-Zero).** Biotinylated probes bind rRNA, and the complexes are removed with streptavidin beads. RNA without rRNA remains in solution.

### 9.3. Different protocol — different data

|  | Poly(A) selection | rRNA depletion (total) |
| --- | --- | --- |
| What enters the library | Mature mRNAs, polyadenylated lncRNAs | Everything except rRNA, including pre-mRNA and non-polyadenylated RNAs |
| Intronic reads | Few | Many |
| Examples seen only in total | — | Replication-dependent histone mRNAs (a stem-loop instead of poly(A), no introns); MALAT1 and NEAT1 (3′ end protected by a triple helix instead of poly(A)) |
| Degraded RNA | Strong 3′ bias | Works much better |
| Cost and simplicity | Cheaper, standard for good-quality RNA | More expensive, some rRNA remains |

**Protocol batch effect.** The choice between the two methods leaves a strong mark on the data. For example, when colon and blood samples are each processed in several replicates with both methods, the two tissues separate, but within each tissue the samples clearly group by protocol. If cohort A was prepared with one method and cohort B with another, differences between them cannot be separated from the artifact. Rule: storage, extraction, library preparation and, where possible, the site should be the same for all samples being compared.

### 9.4. Exon capture for FFPE

For FFPE samples neither approach above works well. A third option uses the same logic as exome sequencing: probes against exons pull out the fragments of interest, and the **bound** molecules are sequenced. This works even for heavily fragmented RNA, where poly(A) selection recovers only 3′ pieces. In FFPE data, samples prepared with exon capture cluster by biology again, while after poly(A) selection they mostly do not.

## 10. Fragmentation, reverse transcription and adapters

**Why fragment.** The insert can be longer than two reads (typically 200–500 nt), but not many times longer. A very long molecule amplifies poorly on the flow cell: it forms bridges less efficiently, and its cluster spreads out and overlaps with neighbours. mRNAs, on the other hand, are thousands of nucleotides long.

**How to fragment.** In standard kits (TruSeq, KAPA) RNA is fragmented with divalent cations (Mg²⁺) at elevated temperature. Double-stranded DNA is fragmented by sonication, enzymes or Tn5 transposase (tagmentation).

### Reverse transcription: how to prime it

Reverse transcriptase is an RNA-dependent DNA polymerase. Like any DNA polymerase, it needs a primer. Since we want to read all transcripts at once, the primer must be universal.

|  | Oligo-dT primer | Random hexamers |
| --- | --- | --- |
| Where it binds | To the poly(A) tail (with an anchor nucleotide at the end so that it sits right at the tail boundary) | At random positions along the whole length |
| When fragmentation happens | After RT: otherwise only fragments carrying the tail would be used | Before RT |
| Coverage | Biased toward the 3′ end | More uniform (with a small bias from hexamer composition) |
| Where it is used | Most single-cell protocols, 3′-tag methods | Standard bulk RNA-seq |

**Why oligo-dT gives 3′ bias.** Reverse transcriptase does not always reach the 5′ end: its processivity is limited and it stalls at RNA secondary structure. So cDNA covers the 3′ part of the transcript more often. This distorts the relationship "gene length → number of reads", which ideally is linear. With random priming it is closer to linear, which makes normalization simpler.

### From cDNA to the final library

The typical sequence of steps after first-strand synthesis (TruSeq-like kits):

1. **Second-strand synthesis** — the RNA:cDNA hybrid is turned into double-stranded DNA. In stranded protocols dUTP is incorporated instead of dTTP (Section 11).
2. **End repair and A-tailing** — a single A is added to the 3′ ends.
3. **Adapter ligation** — adapters with a T overhang are ligated to the double-stranded fragments.
4. **PCR** with primers carrying the indexes and P5/P7 sequences. This is where PCR duplicates arise.
5. **Clean-up** to remove free adapters and adapter dimers (also important for index hopping), and size check.

## 11. Special protocols

### 11.1. Cap-based selection and CAGE

RNA polymerase II transcripts carry a cap at the 5′ end; it is added co-transcriptionally, a few tens of nucleotides after initiation. The cap can be chemically tagged and pulled down:

- **Why in general.** To select full-length molecules that reach the 5′ end (more on this in Lecture 2).
- **CAGE (Cap Analysis of Gene Expression).** The cap is biotinylated, capped molecules are captured with streptavidin, and a short stretch right at the 5′ end is sequenced. This maps **transcription start sites (TSS)** at single-nucleotide resolution. Measuring expression by counting 5′ ends is the basis of the FANTOM project.

**Finding enhancers with CAGE.** An enhancer is a regulatory DNA region located at a distance from a gene and bound by transcription factors. At active enhancers RNA polymerase II itself initiates transcription, usually **in both directions**. This produces enhancer RNAs (eRNAs): short, unstable, capped and usually not polyadenylated. Therefore:

- they are nearly absent from poly(A) libraries;
- in CAGE they appear as a **pair of divergent TSS peaks** on opposite strands, away from annotated genes. FANTOM5 used this signature to build an atlas of tens of thousands of enhancers ([Andersson et al., 2014](https://pmc.ncbi.nlm.nih.gov/articles/5215096)).

Whether eRNAs themselves have a function, or are a by-product of open chromatin, is still debated.

### 11.2. Stranded libraries

In an unstranded library it is unknown which genomic strand the original RNA was transcribed from: a read maps to "+" or "−" with equal probability. In a stranded protocol (the most common is **dUTP**) the second strand is marked with uracil and is not amplified. As a result, R1 always has the same orientation relative to the original RNA. Stranded kits are the default for bulk RNA-seq today (Illumina Stranded mRNA/Total, NEBNext Directional, KAPA).

**Why it matters:**

- Overlapping genes on opposite strands are common. In GENCODE 19 about 19% of genes (\~11,000) overlap a gene on the other strand, especially antisense lncRNAs. Without strand information, reads in such loci are ambiguous ([Zhao et al., 2015](https://pmc.ncbi.nlm.nih.gov/articles/PMC4559181)).
- In the same study, comparing stranded and unstranded libraries from the same blood samples gave 1,751 "differentially expressed" genes — a purely technical effect.
- For bioinformaticians: when counting reads, the correct strandedness must be specified (e.g., `-s` in featureCounts, `libType` in Salmon). Getting it wrong can lose most of the counts.

## 12. Sequencing platforms

| Platform | Principle | Role in transcriptomics |
| --- | --- | --- |
| **Illumina NovaSeq** (6000, X) | Bridge/ExAmp amplification + SBS | Main workhorse of large facilities, highest throughput |
| **Illumina NextSeq / MiSeq** | Same | Cheaper and smaller; typical for small institutes and clinics |
| **MGI / BGI (DNBSEQ)** | DNA nanoballs: rolling-circle amplification of a circularized library in solution, no PCR on the flow cell; fluorescent readout | Similar data to Illumina, lower index hopping; Illumina libraries need conversion before loading; widely used in Russia and China |
| **Oxford Nanopore** | Change in ionic current as a single molecule passes through a pore | Direct RNA sequencing without RT: RNA modifications (e.g., m6A) are visible; long reads for isoforms |
| **PacBio** | Single molecules, highly sensitive fluorescence detector | Long accurate reads of full-length transcripts (Iso-Seq) |

**Why long reads.** Short reads don't show which exons were on the same molecule. If one read falls in exon 1 and another in exon 3, you cannot tell whether they came from an isoform that skips exon 2. A long read covers the whole isoform.

## 13. Key points and glossary

1. RNA-seq measures RNA as an accessible proxy for protein. Correlation with protein is moderate, and protein lags behind in time.
2. Illumina reads clusters of identical molecules one base per cycle. Clusters are needed for a strong signal; phasing limits read length.
3. Up to four sequences are read from one molecule: R1, I1, I2, R2. Unique dual indexes protect against index hopping.
4. Storage method and RNA integrity (RIN, TIN) directly affect the data. Degradation plus poly(A) selection gives 3′ bias.
5. Poly(A) selection and rRNA depletion yield different sets of transcripts. Only samples prepared the same way can be compared.
6. The RT priming strategy (oligo-dT or random primers) determines the coverage profile and when fragmentation happens.
7. Before any analysis, find out whether the library is stranded and which protocol was used.

| Term | Meaning |
| --- | --- |
| Bulk RNA-seq | RNA-seq of a whole piece of tissue, without separating cells |
| Flow cell, lane | The sequencing slide and its independent channels |
| Cluster | Thousands of copies of one library molecule at one spot on the flow cell |
| SBS | Sequencing by synthesis with reversible terminators |
| Base calling, BCL, FASTQ | Converting signal into bases; binary per-cycle files; text files of reads with quality scores |
| Index (i7, i5) | Short library barcode used for multiplexing |
| Demultiplexing | Assigning reads to samples by their indexes |
| Index hopping, UDI | A read acquiring another library's index; protection by unique index pairs |
| Phasing | Loss of synchrony between molecules in a cluster; lowers quality toward the end of a read |
| Paired-end | Reading the insert from both ends |
| FFPE, fresh frozen | Formalin fixation and paraffin embedding; rapid freezing |
| RIN, DV200, TIN | RNA integrity: from electrophoresis, fraction of fragments >200 nt, from read coverage |
| Poly(A) selection, rRNA depletion | Pulling out mRNA with oligo-dT; removing rRNA with probes |
| Oligo-dT / random hexamers | Two ways to prime reverse transcription |
| Stranded (dUTP) | A library that preserves the strand of origin |
| CAGE, TSS, eRNA | Sequencing 5′ ends of capped RNAs; transcription start site; enhancer RNA |
| Perturbation | Any experimental intervention: a compound, a knockout, a knockdown |

## Further reading

- [Illumina: Index hopping](https://www.illumina.com/techniques/sequencing/ngs-library-prep/multiplexing/index-hopping.html)
- [Illumina: Sequencing chemistry (1-, 2-, 4-channel)](https://support-docs.illumina.com/SHARE/IndexAdaptersPooling/Content/SequencingChemistry.htm)
- [Illumina: Impact of RNA degradation on mRNA-seq data](https://knowledge.illumina.com/library-preparation/rna-library-prep/library-preparation-rna-library-prep-troubleshooting-list/000002731)
- [Illumina Stranded mRNA Prep Reference Guide](https://support.illumina.com/content/dam/illumina-support/documents/documentation/chemistry_documentation/illumina_prep/RNA/illumina-stranded-mrna-reference-guide-1000000124518-02.pdf)
- [Thermo Fisher: RNAlater FAQ](https://www.thermofisher.com/order/catalog/product/AM7020/faqs)
- [Zhao et al., 2015 — stranded vs non-stranded RNA-seq](https://pmc.ncbi.nlm.nih.gov/articles/PMC4559181)
- [Andersson et al., 2014 — FANTOM5 enhancer atlas](https://pmc.ncbi.nlm.nih.gov/articles/5215096)
- [MGI DNBSEQ: DNA nanoballs and index mis-assignment](https://pmc.ncbi.nlm.nih.gov/articles/PMC6416933)
