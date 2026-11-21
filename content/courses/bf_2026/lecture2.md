---
lang: en
title: Lecture 2
permalink: /bf.msu.2026/lecture2/
---
# Lecture 2. Single-cell RNA-seq: from tissue to library

This lecture explains how single-cell RNA-seq libraries are made: from dissociating tissue, through isolating cells and barcoding their RNA, to the final Illumina library. Almost every technical step discussed here later shows up in the data — as an artifact, a quality-control metric or a reason to use a particular transformation — so understanding the molecular side pays off in analysis.

## 1. Why single cells: the limits of bulk RNA-seq

An *expression profile* is the list of levels at which each gene is expressed. A bulk experiment gives one expression profile per sample — the average over all cells in the piece of tissue. A single-cell experiment gives one profile per cell, typically thousands to hundreds of thousands of them.

Tissues are heterogeneous: brain, immune infiltrates in a tumour, a developing embryo all consist of many cell types. Averaging over them causes two problems.

1. **You can't tell where a change happened.** Suppose a cancer treatment raises glycolysis genes in a bulk sample. Did this happen in tumour cells, or in immune cells, whose activation and exhaustion also depend on glycolysis? Bulk data describe what changed in the tissue, not in which cells, which limits mechanistic interpretation.
2. **Composition masquerades as regulation.** If one sample contains more CD8 T cells than another, *CD8A* and hundreds of other CD8-specific genes will look "upregulated" even if no cell changed its expression.

## 2. A short history, and why single-cell took off now

Single-cell transcriptomics is almost as old as bulk RNA-seq. The first bulk RNA-seq studies appeared in 2008, and the first single-cell RNA-seq study followed in 2009: Tang et al. sequenced the transcriptome of a single mouse blastomere. Blastomeres are large and RNA-rich, which made them a convenient first target.

The recent boom of single-cell and spatial methods is driven mostly by the falling cost of sequencing, which since the late 2000s has dropped faster than Moore's law. Early protocols did have sensitivity problems — every step has to work on the tiny amount of RNA in one cell, and every added reagent dilutes it further — but these were solved relatively quickly. The real limit was cost: a typical study wants tens or hundreds of thousands of cells, and sequencing remains one of the most expensive parts of an experiment. Cheap sequencing made it affordable to sequence a lot in order to learn comparatively little per read.

## 3. How a single-cell workflow differs from bulk

In bulk RNA-seq the steps (RNA extraction, transcript selection, cDNA synthesis, fragmentation) are largely independent: you can combine a transcript-selection method with any reasonable cDNA-synthesis method. In single-cell RNA-seq the steps are tightly coupled. **Cell isolation** and **cDNA synthesis** in particular are usually designed together, so protocols are described as bundles: "isolate this way, then make cDNA that way".

The one step that is relatively independent — and that you can vary in your own experiment — is tissue dissociation.

## 4. Tissue dissociation and its artifacts

To work with single cells, the tissue must be broken into a suspension of single cells with no cell–cell contacts. This sounds purely technical, but the way you dissociate leaves a strong footprint on the data.

- **Cell-type composition changes.** Cell types differ in how well they survive a given protocol. In a kidney study comparing cold protease dissociation with warm (37 °C) enzymatic dissociation, three replicates each, almost every cell type changed its proportion significantly between the two protocols.
- **Dissociation induces a stress response.** Warm enzymatic digestion switches on heat-shock and immediate-early genes (e.g., *FOS*, *JUN*, *HSP* genes). These signatures appear in many cell types and can be mistaken for biology.
- **No protocol is neutral.** Every method leaves its own traces in cell proportions and in gene expression.

Dissociation is one of the hardest steps of the whole workflow; once you have a good single-cell suspension, most of what follows is routine. Each tissue needs its own recipe because tissue architecture differs. Some tissues are especially difficult: neurons have very long processes, and dissociation tears axons and dendrites, damaging the cells. Blood needs no dissociation at all, which is why new methods are usually demonstrated on **PBMC** (peripheral blood mononuclear cells): they are easy to obtain and remove one source of technical variation.

This is also why building a cell atlas across organs is hard. Even an identical cell placed in two different tissues would come out with different profiles, because each tissue is dissociated differently. The general rule applies: groups you compare must be prepared with an experimental setup that is as similar as possible.

## 5. Single-nucleus RNA-seq (snRNA-seq)

In snRNA-seq you isolate and sequence single **nuclei** instead of whole cells.

**Why use it.**

- Nuclear isolation is much simpler than whole-cell dissociation and very similar across tissues. You avoid the trade-off of dissociation: digesting enough to separate the cells, but not so much that they die or mount a stress response.
- For some tissues (brain, kidney) it is often the only practical option: cells are so tightly connected that they are destroyed when separated.
- It works on frozen tissue, where intact cells cannot be recovered.

**How it works.** The cell membrane is lysed while the nuclear envelope is kept intact. Nuclei are then separated from cytoplasmic debris by centrifugation. Care is needed here: the outer nuclear membrane is continuous with the endoplasmic reticulum, so isolated nuclei carry fragments of ER with attached ribosomes and cytoplasmic RNA. Any mixing of phases during the clean-up adds cytoplasmic contamination.

**What is actually measured.** The nucleus contains the cell's full set of pre-mRNAs but only a small fraction of its mature mRNAs, since most mRNA is exported to the cytoplasm. Even though single-cell protocols prime reverse transcription with oligo-dT, much of the snRNA-seq signal comes from pre-mRNA: oligo-dT also binds internal A-rich stretches inside introns. As a result, a large share of reads (often more than half) maps to introns. In analysis, intronic reads must be counted (for example, Cell Ranger's include-introns mode), otherwise most of the data is lost and gene-length biases appear.

## 6. Isolating single cells: plates vs droplets

Once you have a single-cell suspension, the task is to run an RNA-seq reaction on each cell separately.

**Plate-based isolation.** The earliest experiments picked cells one by one with a pipette under a microscope. Today a fluorescence-activated cell sorter (FACS) dispenses single cells automatically into the wells of a plate, usually a 384-well plate. Each well then gets its own reaction. Other options include capillary pipettes and laser capture microdissection.

The limitation is throughput. Even with robots, preparing libraries for \~10,000 cells this way takes weeks, while modern datasets reach hundreds of thousands to millions of cells.

**Droplet-based isolation.** Microfluidics encapsulates single cells in tiny droplets that act as reaction vessels. This is now the most widely used approach, and the main topic of this lecture.

Droplets removed the throughput limit, and the number of cells per experiment has grown every year since. Ten years ago a dataset of 100,000 cells was a publishable result on its own; today a dataset alone is not enough, and a study has to show new biology. Single-cell transcriptomics is like a new microscope: at first it was worth pointing at everything, and now most tissues have been looked at.

## 7. Droplet microfluidics and 10x Chromium

The most popular droplet platform is the **10x Genomics Chromium** (the Chromium Controller, and the newer Chromium X). All 10x single-cell assays are droplet-based.

**The core idea: isolate, then label.** Cells must be *single* and *isolated*. In a plate, wells are separated by plastic; in a droplet system, droplets are separated by oil. In both cases the goal is to give all RNA from one cell a shared label, so that the libraries from all cells can be pooled and sequenced together and the reads assigned back to their cell afterwards.

**How droplets form.** In a microfluidic chip, aqueous channels meet: one carries barcoded **gel beads**, one carries cells, one carries reagents (reverse transcriptase and so on). This stream then meets a faster flow of oil with surfactant. The oil pinches the aqueous stream into droplets, producing a water-in-oil emulsion. Because the droplets are surrounded by oil, their contents cannot mix. 10x calls each droplet a **GEM** (Gel bead-in-EMulsion).

**Why a bead.** In a plate you can pipette well-specific primers into each well. In millions of droplets you can't, so the primers are delivered on a bead. Each bead carries millions of primers that share one **cell barcode** (unique to that bead) and differ in their **UMI** (Section 10).

**Loading statistics.** Cells arrive at the junction at random, so the number of cells per droplet follows a Poisson distribution. Cells are loaded at low concentration, so most droplets contain no cell and few contain two. 10x gel beads, by contrast, are packed so densely that they enter droplets in a regular stream, and more than 90% of droplets contain exactly one bead. As a result, most cells end up in a droplet with a bead.

**Releasing the primers.** The 10x gel bead is a dissolvable hydrogel, larger than a typical cell. Inside the droplet a reducing agent dissolves the bead and releases the barcoded primers, so reverse transcription happens in solution inside the droplet. How to free the primers was a key engineering problem. Earlier platforms solved it differently: inDrops used beads with photocleavable linkers released by UV light. Drop-seq used hard resin beads that stay intact, with mRNA captured on the bead and reverse transcribed after the droplets are broken.

**Throughput and robustness.** One standard chip runs 8 samples in parallel (high-throughput chips run more). Because the microfluidics and reactions are automated, it is hard to get library preparation wrong. That reliability is a major reason 10x became the default.

## 8. Barcoded reverse transcription and template switching

### The bead primer

Each primer on a 10x 3′ gel bead has, from 5′ to 3′:

1. a partial **Illumina Read 1** sequence (a known handle for later PCR and sequencing);
2. the **cell barcode** (16 nt in 10x 3′ v3) — identical on all primers of one bead, different between beads; it is the cell's "passport";
3. the **UMI** (12 nt in v3) — different on each primer molecule;
4. **oligo-dT**, ending in **VN**: V = A, C or G (not T), N = any base. The anchor forces the primer to bind at the very start of the poly(A) tail. Without it, oligo-dT could anneal anywhere along the 100–250-nt tail, and the first part of every cDNA would be wasted on T's.

### No transcript selection, so oligo-dT priming

In bulk RNA-seq, rRNA is removed by poly(A) selection or depletion before library preparation. In droplets this is impossible: volumes are tiny, everything happens in one reaction, and selection steps lose a lot of material. Instead, priming reverse transcription from oligo-dT does the selection: only polyadenylated RNA is copied.

The drawback known from bulk applies here too. Reverse transcriptase has limited processivity, so it often stops before reaching the 5′ end. Note the precise wording: it works on transcripts of any length, but on long transcripts it frequently produces only the 3′ part. Some technologies accept these truncated products as they are; most others add template switching.

### Template switching (SMART)

Template switching was introduced with the SMART method (Switching Mechanism At 5′ end of RNA Template), used by 10x and by the Smart-seq protocols.

1. MMLV-type reverse transcriptases have **terminal transferase activity**. When the enzyme reaches the 5′ end of the RNA, it adds a few non-templated nucleotides, mostly C's (classically +CCC), to the 3′ end of the cDNA. The 5′ cap of mRNA makes this more efficient.
2. A **template-switching oligo (TSO)**, which ends in three G's (usually ribo-G), base-pairs with this C overhang.
3. The reverse transcriptase **switches template** from the mRNA to the TSO and copies it. The cDNA now carries a known sequence at its 3′ end, which corresponds to the mRNA's 5′ end.

A first-strand cDNA now has known sequences at both ends: the bead's Read 1 handle on one side and the TSO on the other. After the droplets are broken and all cells' cDNA is pooled, **PCR with primers against these two handles** amplifies the cDNA. This is how the tiny amount of cDNA from each cell becomes enough to build a library. A side effect is that the amplified cDNA is enriched for molecules whose reverse transcription reached the 5′ end, because truncated products lack the TSO handle and are not amplified exponentially.

## 9. Library construction, read structure and 3′ bias

The amplified full-length cDNA is too long for Illumina (Lecture 1: the insert can be somewhat longer than the reads, but not much). So it is fragmented again, this time in the pooled mixture from all cells.

1. **Enzymatic fragmentation** with a non-sequence-specific fragmentation enzyme (not restriction enzymes, which would cut only at specific sites), followed by end repair and A-tailing.
2. **Adapter ligation** adds the Read 2 sequence to the fragment ends.
3. **Sample index PCR** adds P5/P7 and the sample indexes. Current 10x kits use dual indexes; early v3 kits used a single sample index.

**Only one fragment per cDNA is useful.** After fragmentation, each cDNA yields several pieces. Only the piece that still carries Read 1 + cell barcode + UMI is informative, because the barcode tells us which cell it came from. Internal pieces and the TSO end have no barcode, and since all cells are pooled at this point, they can't be assigned to a cell. The barcode sits next to the poly(A) tail, so the sequenced fragments come from the **3′ end** of transcripts. Even though the cDNA was full-length, the final 10x 3′ library is 3′-biased.

**Read structure (10x 3′ v3).**

| Read | Length | Content |
| --- | --- | --- |
| Read 1 | 28 nt | Cell barcode (16) + UMI (12); anything beyond would be poly(T) |
| i7 / i5 | 10 nt each | Sample indexes |
| Read 2 | \~90 nt | cDNA insert — used to identify the gene |

When a run contains only 10x libraries, the facility sets Read 1 to \~28 cycles so as not to pay for sequencing poly(T). In a shared 2×150 run, Read 1 is simply trimmed after the barcode and UMI.

For counting gene expression, 3′ bias is not a problem: each UMI marks one original molecule wherever on the gene the read falls. It matters when you need sequence from elsewhere in the transcript (Sections 11 and 13).

## 10. PCR duplicates and UMIs

**Amplification bias.** Single-cell libraries go through two PCRs (cDNA amplification and sample index PCR) starting from very little material. Ideally each cycle doubles every molecule (10 cycles ≈ 1,000×), but efficiency is below 100% and varies between molecules (length, GC content). When the starting number of molecules is small, chance in the first cycles matters a lot. A molecule that happens to be copied in cycle 1 gets a head start that is multiplied in every later cycle. The final read counts therefore no longer reflect the original numbers of molecules.

**Why bulk-style deduplication doesn't work.** In bulk paired-end RNA-seq, two read pairs with identical start *and* end coordinates are almost certainly PCR copies of one fragment. This works because fragmentation happens before PCR, and random fragmentation rarely produces the same two ends twice. In 10x data this logic fails in both directions.

- **Duplicates are missed.** The main amplification (cDNA PCR) happens *before* fragmentation. Copies of one molecule are then fragmented independently and end up with different Read 2 coordinates.
- **Different molecules look like duplicates.** All reads start next to the poly(A) tail, so independent molecules of the same transcript have nearly the same coordinates.

**UMIs (unique molecular identifiers).** Each primer on the bead carries a random UMI, so each original mRNA molecule receives its own tag before any amplification. All PCR copies of that molecule share the cell barcode, the gene and the UMI. Reads with the same barcode + gene + UMI are collapsed into one molecule. A 12-nt UMI has \~16.7 million possible sequences, so two molecules of the same gene in one cell rarely receive the same UMI by chance.

The consequence for analysis: **single-cell expression is measured in UMI counts** (the number of distinct molecules per gene per cell), not read counts as in bulk.

**UMIs elsewhere.** UMIs are also essential whenever many independent molecules naturally share the same coordinates:

- **Amplicon sequencing** (e.g., the V4 region of 16S rRNA in bacterial metagenomics): every amplicon starts and ends at the same primers, so coordinates can't separate molecules.
- **CLIP-seq family** (RNA-binding protein crosslinking, e.g., iCLIP, eCLIP): reads pile up at precise binding sites. In ChIP-seq, coordinate-based deduplication is still usually acceptable because fragments around a binding site are more varied.

## 11. 5′ protocols and immune receptor sequencing

Sometimes we need the sequence itself, not just the count. The main case is **T- and B-cell receptors**. Their hypervariable **CDR3** region (complementarity-determining region 3) is created by V(D)J recombination and differs from clone to clone. The V(D)J part of the receptor transcript lies near its **5′ end**, far from the poly(A) tail, so a 3′ library doesn't reach it.

In a 3′ protocol the coverage is tied to the 3′ end because the barcode is attached at the poly(A) side. A **5′ protocol** moves the barcode to the other end: the cell barcode and UMI sit on the **TSO**, which is delivered on the bead, while oligo-dT is added free in solution. The final library then comes from the 5′ end of transcripts. From the full-length cDNA, TCR/BCR transcripts can additionally be amplified with receptor-specific primers (V(D)J libraries).

Ideally 3′ and 5′ data from the same cells would give the same expression values. In practice the differences are substantial, so the field standard is the 3′ assay, with 5′ chemistry used mainly when immune receptor sequences are needed.

## 12. Singlets, doublets, empty droplets and ambient RNA

Cells and beads are distributed into droplets by chance, so not every droplet has "one bead, one cell":

| Droplet contents | Name | What you see in the data |
| --- | --- | --- |
| Cell, no bead | — | Nothing: the cell is lost without trace (rare with 10x bead loading) |
| Bead, no cell | **Empty droplet** | A barcode with a handful of UMIs from ambient RNA |
| Bead + one cell | **Singlet** | The desired case |
| Bead + two or more cells | **Doublet / multiplet** | Two cells' transcriptomes under one barcode, mistaken for one cell |

**Doublets.** Their rate rises with the number of cells loaded. For standard 10x 3′ v3.1 it is roughly 0.8% per 1,000 recovered cells, i.e. about 8% at 10,000 cells. There are two sources: Poisson co-encapsulation, which is unavoidable and scales with loading, and incompletely dissociated cell clumps. The frequency of doublets between particular cell types can even reflect which cells are neighbours in the tissue. Doublets of different cell types (e.g., a T cell + a tumour cell) are the most harmful, because they look like a new, intermediate cell type.

**Ambient RNA.** Some cells always die during dissociation and spill their RNA into the suspension. This "soup" ends up in every droplet: a small fraction (a few percent) of the UMIs in a real cell, and all of the UMIs in an empty droplet. A typical example: haemoglobin genes appear at low levels in all cell types because red blood cells lysed during preparation. Computational correction (e.g., SoupX, CellBender) uses two ideas. The ambient profile is roughly the same in every droplet, and it resembles the cell types that released it.

**Empty droplets.** Empty droplets still contain a bead and ambient RNA, so they get barcodes with a few UMIs. This is why the raw output contains far more barcodes than the cells you loaded — you may load 10,000 cells and see 100,000 or more barcodes. *Cell calling* separates real cells from empty droplets (e.g., the EmptyDrops method). Doublets are flagged with tools such as Scrublet or scDblFinder. Both topics come back in the analysis lectures.

## 13. Plate-based full-length protocols (Smart-seq) and isoforms

In plate-based protocols each cell sits in its own well, which makes different library designs possible. The best-known family is **Smart-seq**: Smart-seq (2012) was developed for single cells from the start, and Smart-seq2 (2013–2014) improved its sensitivity and became the standard.

1. Oligo-dT priming and template switching produce full-length cDNA, as in 10x (but without a cell barcode on the primer).
2. The cDNA is pre-amplified by PCR.
3. The cDNA is fragmented with Tn5 transposase, and sample indexes are added. Because each well is separate, **every fragment is usable**, not just the 3′ one.
4. Each cell becomes its own sample: 500 cells give 500 pairs of FASTQ files, processed much like small bulk samples.

|  | 10x Chromium (3′) | Smart-seq2 |
| --- | --- | --- |
| Coverage | 3′ end only | Full length of transcripts |
| Sensitivity | Lower (often \~1,000–5,000 genes per cell, depending on cell type and chemistry) | Higher (often \~5,000–8,000+ genes per cell) |
| Throughput | Thousands to hundreds of thousands of cells | Hundreds to a few thousand cells |
| UMIs | Yes | No — PCR duplicates can't be removed |

**Smart-seq3** adds UMIs on the TSO, at the 5′ end. Only fragments from the 5′ end carry a UMI, so the library is a mixture of UMI-tagged 5′ reads (for counting molecules) and internal reads without UMIs (for full-length coverage).

**Isoforms and mutations.** Full-length coverage makes it possible to estimate isoform usage and call variants. Variant calling in single cells is still noisy and needs care. For example, the isoforms of CD45 (gene *PTPRC*), such as CD45RA and CD45RO, differ by alternative exons and distinguish naive from memory T cells; Smart-seq coverage can resolve them. Computational tools estimate isoform proportions from short reads, assuming a known set of isoforms. For complex or novel isoforms, long reads are needed. A convenient feature of the 10x workflow is that the intermediate cDNA is full-length and already carries the cell barcode and UMI. It can therefore be sequenced directly on Nanopore or PacBio to read whole isoforms per cell, or used as a template for any targeted amplification.

## 14. Key points and glossary

1. Bulk data average over cell types: changes can't be localized, and composition shifts look like expression changes.
2. Dissociation is one of the hardest steps and always leaves traces: altered cell-type proportions and stress-response genes. Compare only samples dissociated the same way.
3. snRNA-seq avoids many dissociation problems. It measures mostly nuclear pre-mRNA, so intronic reads must be counted.
4. Droplet methods label all RNA from one cell with a bead-specific cell barcode. Cells are loaded by Poisson statistics, so empty droplets and doublets are unavoidable.
5. Template switching gives cDNA a second known handle for PCR. However, the final 10x 3′ library covers only the 3′ end, because only barcoded fragments can be assigned to a cell.
6. UMIs tag each molecule before amplification. Single-cell expression is counted in UMIs, not reads.
7. 5′ chemistry is used for immune receptor sequences. Smart-seq gives full-length, more sensitive but lower-throughput data without UMIs (UMIs only at the 5′ end in Smart-seq3).

| Term | Meaning |
| --- | --- |
| Dissociation | Breaking tissue into a suspension of single cells |
| snRNA-seq | Sequencing single nuclei instead of whole cells |
| PBMC | Peripheral blood mononuclear cells |
| FACS | Fluorescence-activated cell sorting; can dispense single cells into plates |
| GEM | Gel bead-in-emulsion: a 10x droplet with one bead |
| Cell barcode | Sequence shared by all primers on one bead; identifies the cell |
| UMI | Random sequence unique to each primer; identifies the original molecule |
| Oligo-dT VN | Anchored oligo-dT primer that binds at the start of the poly(A) tail |
| Template switching, TSO | Reverse transcriptase adds C's at the RNA 5′ end and switches to copy a G-ending oligo, adding a known 5′ handle |
| 3′ / 5′ assay | Library built from the 3′ or 5′ end of transcripts |
| CDR3 | Hypervariable region of T/B-cell receptors created by V(D)J recombination |
| Doublet | Two cells sharing one barcode |
| Empty droplet | A droplet with a bead but no cell; contains only ambient RNA |
| Ambient RNA | Free RNA from dead or lysed cells that contaminates all droplets |
| Smart-seq2 / Smart-seq3 | Plate-based full-length protocols; Smart-seq3 adds 5′ UMIs |

## Further reading

- [Tang et al., 2009 — mRNA-Seq whole-transcriptome analysis of a single cell (protocol paper)](https://pmc.ncbi.nlm.nih.gov/articles/PMC3847604)
- [Ramsköld et al., 2012 — Smart-Seq](https://www.nature.com/articles/nbt.2282)
- [Template switching and non-templated addition by MMLV reverse transcriptases](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6885630/)
- [10x Genomics: intronic and antisense reads in single-cell data](https://cdn.10xgenomics.com/image/upload/v1660261286/support-documents/CG000376_TechNote_Antisense_Intronic_Reads_SingleCellGeneExpression_RevA.pdf)
- [Chamberlin et al., 2024 — molecular sampling in single-cell vs single-nucleus RNA-seq](https://pmc.ncbi.nlm.nih.gov/articles/PMC10984380)
- [10x Genomics: Chromium Single Cell 3′ v3.1 (Dual Index) user guide](https://ostr.ccr.cancer.gov/wp-content/uploads/2023/06/CG000315_ChromiumNextGEMSingleCell3-_GeneExpression_v3.1_DualIndex__RevE.pdf)
