---
lang: en
title: Lecture 4
permalink: /bf.msu.2026/lecture4/
---
# Lecture 4. Quality control of single-cell data and working with AnnData

This lecture is about **quality control (QC) of the count matrix**: telling real cells from empty droplets, damaged cells and doublets. This is a different kind of QC from read-level QC (base qualities, adapters). The practical part introduces **scanpy** and its data container **AnnData**, which we will use for the rest of the course.

## 1. Single-cell data are sparse

A droplet-based experiment captures only a minority of the mRNA molecules in each cell — roughly 10–30%, depending on chemistry and cell type. As a result, most genes in a given cell are observed 0 times, and many of the rest only once or twice. Most entries of the count matrix are zero.

Keep this intuition in mind. An aggregate coverage plot summed over all cells and genes can look reasonable. For one gene in one cell, though, there are usually only one or two reads. The same sparsity is why isoforms and individual exons are hard to study with standard 10x data: coverage is concentrated at the 3′ end, and per-cell counts are tiny.

## 2. Empty droplets, singlets, doublets: what QC must separate

Cell Ranger's main output is a **genes × barcodes matrix of UMI counts**: for each barcode, how many distinct UMIs were detected for each gene. It comes in two versions: **raw** (all barcodes) and **filtered** (only barcodes called as cells). Remember: the barcode is the cell's "passport". Everything with the same barcode is treated as one cell.

Droplets fall into three main groups, plus two rare cases.

- **Empty droplets.** These contain a bead but no cell. They are not truly empty: ambient RNA from dead or lysed cells gets in, is reverse transcribed and receives the bead's barcode. Such barcodes have a handful of UMIs. They are by far the most numerous barcodes in the raw matrix.
- **Singlets.** One cell and one bead — what we want to analyse.
- **Doublets.** Two (or more) cells share one bead, so their transcriptomes are merged under one barcode. They arise by chance co-encapsulation (Lecture 2) and from cell clumps that were not fully dissociated.
- **Cells without a bead** are lost without a trace. 10x avoids this by loading beads so densely that almost every droplet gets exactly one.
- **Droplets with two beads** are rare but do occur. They split one cell between two barcodes.

How cleanly a library comes out also depends on handwork. Every lysed cell adds to the ambient RNA, so gentle pipetting and careful handling of cells and nuclei directly reduce noise.

QC removes, in order:

1. empty droplets;
2. low-quality singlets (damaged or dying cells);
3. doublets.

## 3. Removing empty droplets

**The simple approach: a threshold on UMI counts.** A real cell contains far more RNA than the ambient "soup" in a droplet. Real cells typically have thousands of UMIs, often more than 10,000; empty droplets have a few to a few dozen. So if you sum the UMIs per barcode and plot a histogram (on a log scale), you see a **bimodal distribution**. A threshold placed in the valley between the two peaks separates empty droplets (left) from cells (right). This simple approach works well and is still widely used.

**Genes per cell often separates even better.** Count how many genes have a non-zero count in each barcode. Ambient RNA is dominated by a few very highly expressed genes (e.g., haemoglobin in blood-contaminated samples), so many UMIs in an empty droplet fall into the same genes. The gap between empty droplets and cells is therefore even wider in genes per cell than in UMIs per cell.

**The knee plot (barcode rank plot).** This is the standard way to show the same information.

- Sort barcodes by total UMIs and plot UMI count against rank, both axes on a log scale.
- The curve is the cumulative distribution turned on its side. A plateau of high-UMI cells is followed by a steep drop to the many low-UMI empty droplets.
- The **knee** and **inflection point** of the drop correspond to the valley of the histogram.

The histogram and the knee plot carry the same information; it's worth being able to read both.

**EmptyDrops** is the most widely used refinement, and an implementation of it is built into Cell Ranger (version 3 and later).

1. Barcodes above the knee are kept as cells.
2. Barcodes with very few UMIs (by default at most 100 in the original R implementation) are taken as certainly empty. They are used to estimate the **ambient profile**: the gene proportions in the soup.
3. For each barcode in the uncertain middle zone, EmptyDrops tests whether its counts could plausibly be a random sample from the ambient profile.
4. The p-values are corrected for multiple testing (FDR). Barcodes whose profile differs significantly from the soup are kept as cells, even if they have few UMIs.

**Why this matters: small cells.** Some cells are biologically small or RNA-poor. **Neutrophils** are the classic example. They contain little mRNA and are rich in RNases and other degradative enzymes that interfere with reverse transcription. They therefore come out with low UMI counts and can be removed by standard filtering. If neutrophils (or other granulocytes) matter for your question, filter carefully. In most datasets, though, the low-UMI fraction is mostly debris and damaged cells.

**After Cell Ranger.** Even with EmptyDrops built in, always plot the distributions of the filtered matrix yourself. A second, low mode (for example, cells with fewer than \~1,000 UMIs when the main mode is \~12,000) usually consists of damaged or dying cells. Such cells later form junk clusters or blur the boundaries between real ones, so an extra threshold is often worthwhile.

## 4. Removing damaged cells: the mitochondrial fraction

When a cell is damaged during dissociation, its plasma membrane is breached and cytoplasmic mRNA leaks out. Mitochondria, enclosed by their own two membranes, keep their transcripts. As a result, **damaged and dying cells show an increased percentage of mitochondrial UMIs**. The percentage of mitochondrial counts per cell is one of the most useful QC metrics.

- **Plot first, then set a threshold.** Plot the distribution and cut off the high tail. The right threshold is dataset- and tissue-dependent. In some datasets the main mode lies at 0–5%, so a cutoff around 5–10% is sensible. In others, for example metabolically active tissues such as heart or kidney, it lies at 0–20%.
- **Single-nucleus data** should contain almost no mitochondrial reads, since mitochondria are removed with the cytoplasm. A high mitochondrial fraction there indicates cytoplasmic contamination.
- **Finding mitochondrial genes.** In human references they start with `MT-` (13 protein-coding genes); in mouse, with `mt-`. Some references (e.g., some kallisto indexes) don't use this prefix, and the list has to be made by hand (*ATP8*, *ND6*, etc.).

## 5. Doublets and Scrublet

**Why doublets are dangerous.** A doublet of two different cell types looks like a cell expressing markers of both. Doublets can form their own cluster that looks like a new cell type or an intermediate state.

A cautionary example from the lecturer's own work. In a follicular lymphoma dataset analysed without doublet removal, a cluster of CD4⁺CD8⁺ "double-positive" T cells appeared. Several days of analysis went into it before it turned out to be CD4 + CD8 T-cell doublets. Double-positive T cells do exist: they are a normal stage of thymic development, and smaller double-positive populations have been described in some peripheral tissues and diseases. But a double-positive cluster in a single-cell dataset should first be checked for doublets.

**A general lesson.** If your data seem to show something completely new that nobody has seen before, the first hypothesis should be an artifact. It is not impossible that it's real, just much less likely.

**Why doublets can be detected.** A doublet's profile is roughly the *sum* of two cells, so it also tends to have higher UMI and gene counts. Real intermediate states are not simple mixtures. A cell differentiating from state A to state B is not the average (A + B)/2: transitions usually switch on their own genes, absent from both A and B. That is the main argument for a real "bridge" population between two clusters.

**Scrublet.**

1. Simulate artificial doublets by adding up the profiles of random pairs of observed cells.
2. Embed real and simulated cells together (via PCA) and build a nearest-neighbour graph.
3. For each real cell, compute a **doublet score** from the fraction of simulated doublets among its neighbours. Real doublets sit among simulated ones, while singlets are surrounded mostly by real cells.
4. Pick a threshold automatically, using the score distribution of the simulated doublets as a reference, and return both scores and binary predictions.

Scrublet mainly catches doublets of two *different* cell types, and those are the ones that matter. Doublets of two cells of the same type are mostly harmless: they blur a cluster but don't create a new one. Scrublet should be run **separately for each sample** (each 10x channel), because doublets form within one channel.

Scrublet's automatic threshold doesn't always work: the score distribution is often not clearly bimodal, and visible doublet clusters may remain. A practical, conservative alternative is a fixed threshold of about 0.15. Also check whether whole clusters have high doublet scores.

## 6. How to think about QC thresholds

There is no universal law for how to filter. Analysis is a tool for getting biological insight, not a goal in itself. We filter empty droplets, damaged cells and doublets because they stop us from finding cell types, describing their states and comparing proportions: they create junk clusters, connect unrelated ones and add noise.

In practice:

- Always look at the distributions (UMIs, genes, mitochondrial fraction, doublet score) and choose thresholds that remove clear outliers.
- Small differences in thresholds (e.g., 1,000 vs 2,000 genes) usually change a few dozen cells and don't affect conclusions.
- What matters is avoiding situations where a large share of cells (say 30%) are low quality.
- If your conclusions change with a small change in thresholds, they are not robust.

## 7. The Cell Ranger web summary

Before doing your own QC, it is worth looking at what Cell Ranger has already reported. Cell Ranger is run with a single command (reference, FASTQ path, sample name) but takes a long time, so in class we only look at its output. Alongside the matrices it writes `web_summary.html` with three blocks of QC. Cell Ranger flags in bold any metric outside its expected range. This is useful because it's often hard to know at what value to start worrying (is 90% mapped fine? 80%?).

1. **Sequencing.**
   - **Q30 metrics:** the fraction of bases with Phred quality ≥ 30 (error probability ≤ 0.1%), separately for barcode, UMI and RNA reads.
   - **Valid barcodes:** the fraction of reads whose barcode matches the 10x whitelist (after error correction).
   - **Number of reads.** For planning, 10x recommends at least \~20,000 reads per cell; 20,000–50,000 is common, and more reads detect more genes. Total reads ≈ expected cells × reads per cell.
2. **Mapping.** The fraction of reads mapped to the genome, and to exonic, intronic and intergenic regions. Low mapping often means the wrong reference (wrong species).
3. **Cells.** The barcode rank (knee) plot, estimated number of cells, mean reads per cell, median genes and UMIs per cell.

## 8. Tools: Colab, scanpy and scverse

The practical sessions run in **Google Colab**. You can use its built-in terminal, or run shell commands from a notebook cell with a leading `!`. Install scanpy with `pip install scanpy`; Colab may warn about package version conflicts.

**scanpy** (imported as `sc`) is the main Python library for single-cell analysis. It belongs to the **scverse** ecosystem:

- **core packages:** anndata, scanpy, muon (multimodal data), squidpy (spatial data), scvi-tools and others;
- **ecosystem packages:** many more, contributed by the community. These are often excellent but less guaranteed to be maintained, so check for recent activity before relying on one.

A good way to learn what is possible is to read scanpy's tutorials and browse its API documentation, looking up unfamiliar functions (diffusion maps, trajectory inference…) as you go. Nobody remembers every argument; copying commands from tutorials, including your own, is normal practice.

`sc.settings.verbosity = 3` makes scanpy report what each function does and where it stores the results.

## 9. AnnData: structure and practical tips

`sc.read_10x_h5("filtered_feature_bc_matrix.h5")` reads Cell Ranger output into an **AnnData** object. (HDF5 is a hierarchical binary format that stores several related arrays in one file.) AnnData keeps the matrix and all its annotations aligned with each other.

| Slot | What it holds | Shape |
| --- | --- | --- |
| `adata.X` | The main matrix: rows = cells (observations), columns = genes (variables) | n\_obs × n\_vars |
| `adata.obs` | Data frame describing cells: sample, tissue, cluster, cell type, QC metrics… | n\_obs rows |
| `adata.var` | Data frame describing genes: gene IDs, feature type, mitochondrial flag… | n\_vars rows |
| `adata.obsm` | Low-dimensional representations of cells, e.g. `X_pca`, `X_umap` | n\_obs × k each |
| `adata.varm` | Per-gene matrices, e.g. PCA loadings | n\_vars × k each |
| `adata.layers` | Alternative versions of X, e.g. raw counts vs normalized values | n\_obs × n\_vars each |
| `adata.uns` | Unstructured metadata (parameters, colour maps…) | any |

**Everything must match the cells and genes.** An `obsm` entry must have exactly one row per cell, so you can't store, say, a PCA from another dataset there. Subsetting cells (e.g., after QC) subsets every slot consistently. Filtered-out cells are gone from that object, so keep a copy if you may need them.

**Practical tips.**

- **Unique gene names.** Cell Ranger references contain some different genes (different Ensembl IDs) that share one symbol. Run `adata.var_names_make_unique()`, which appends `-1`, `-2`… to the repeats, so that plotting by gene name is unambiguous.
- **Barcode names.** The `-1` suffix on 10x barcodes marks the library (GEM well). It matters only when several libraries are combined in one Cell Ranger run. A common practice is to replace it with a sample prefix, e.g. `sample001_AAACCTG…`, so that barcodes stay unique when samples are merged.
- **Categorical columns.** Store repetitive labels (sample, tissue, cluster, cell type) as pandas `category`. Each distinct value is stored once and rows hold small integer codes, which can save a lot of memory. For columns where nearly every value is unique, categoricals don't help, and numbers should stay numeric.
- **Mitochondrial flag.** `adata.var["mt"] = adata.var_names.str.startswith("MT-")` (use `"mt-"` for mouse).
- **Slicing.** AnnData objects can be sliced like data frames, e.g. `adata[adata.obs["sample"] == "sample001"]`, or by a boolean mask over genes.
- **Building one by hand.** You can create an object from any matrix: `ad.AnnData(X=matrix, obs=obs_df, var=var_df)`. This is useful when reading output of a tool scanpy has no reader for.
- **Saving and sharing.** `adata.write_h5ad("file.h5ad")` and `sc.read_h5ad("file.h5ad")` save and load the whole object in one file. `.h5ad` files are also how processed datasets are commonly shared (e.g., Zenodo, CELLxGENE, GEO supplementary files).
- **Plotting.** scanpy's plotting functions know where things are stored, e.g. `sc.pl.embedding(adata, basis="X_umap", color="cell_type")`.

## 10. Sparse matrices and memory

Memory (RAM) is a real constraint in single-cell analysis; even servers with a terabyte of RAM fill up. Consider 20,000 genes × 1,000,000 cells = 2×10¹⁰ values. At 4 bytes per value (float32) a dense matrix needs about 80 GB, and even at 1 byte per value it needs about 20 GB.

Since most values are zero, `adata.X` is usually stored as a **sparse matrix**, which records only the non-zero values and their positions. There are two common layouts:

- **CSR** (compressed sparse row): fast access to rows, i.e. cells. This is the usual layout for `adata.X`.
- **CSC** (compressed sparse column): fast access to columns, i.e. genes.

Converting to dense (`adata.X.toarray()`) causes a memory spike; avoid it on real datasets. To create a sparse matrix yourself, use `scipy.sparse.csr_matrix(dense_array)`. For data too large for memory, AnnData can also work with backed (on-disk) mode, but fewer functions support it.

## 11. QC in code: a minimal workflow

```python
import scanpy as sc
import numpy as np

adata = sc.read_10x_h5("filtered_feature_bc_matrix.h5")
adata.var_names_make_unique()

# QC metrics: total UMIs, genes per cell, % mitochondrial
adata.var["mt"] = adata.var_names.str.startswith("MT-")
sc.pp.calculate_qc_metrics(adata, qc_vars=["mt"], inplace=True, log1p=False)
# -> adata.obs["total_counts"], ["n_genes_by_counts"], ["pct_counts_mt"]

# The same by hand, for understanding
umis = np.asarray(adata.X.sum(axis=1)).ravel()
genes = np.asarray((adata.X > 0).sum(axis=1)).ravel()

# Look at the distributions before choosing thresholds
sc.pl.violin(adata, ["total_counts", "n_genes_by_counts", "pct_counts_mt"], multi_panel=True)

# Example thresholds (dataset-specific!)
adata = adata[(adata.obs.total_counts >= 2000) &
              (adata.obs.n_genes_by_counts >= 600) &
              (adata.obs.pct_counts_mt <= 20)].copy()

# Doublets (run per sample)
sc.pp.scrublet(adata)
# -> adata.obs["doublet_score"], adata.obs["predicted_doublet"]
adata = adata[~adata.obs.predicted_doublet].copy()

# Keep raw counts before any transformation
adata.layers["counts"] = adata.X.copy()
```

**Be careful with in-place transformations.** Many functions modify the object in place. Re-running a notebook cell can, for example, log-transform the data twice without any warning. Some tools expect raw integer counts and others expect log-normalized values. So always know what is currently in `adata.X`, and keep raw counts in a layer.

## 12. Key points and glossary

1. Single-cell matrices are sparse: only a minority of each cell's mRNA is captured, and most entries are zero.
2. QC of the count matrix removes empty droplets, damaged cells and doublets, in that order.
3. Empty droplets separate from cells by UMIs and, even better, by genes per barcode. The knee plot shows the same thing; EmptyDrops (built into Cell Ranger) tests uncertain barcodes against the ambient profile. Still check the filtered distributions yourself.
4. A high mitochondrial fraction marks damaged cells; thresholds depend on the dataset and tissue.
5. Doublets can create fake cell types. Scrublet finds cells resembling simulated doublets; run it per sample and check its threshold.
6. Thresholds are tools, not laws: choose them by looking at the data, and check that conclusions are robust.
7. AnnData keeps X, obs, var, obsm, layers and uns aligned. Use sparse matrices and categorical columns to save memory, and keep raw counts in a layer.

| Term | Meaning |
| --- | --- |
| Raw / filtered matrix | All barcodes / only barcodes called as cells |
| Ambient RNA | Free RNA from lysed cells present in every droplet |
| Knee (barcode rank) plot | UMIs per barcode vs barcode rank, log–log |
| EmptyDrops | Test of whether a barcode's profile differs from the ambient profile |
| Mitochondrial fraction | Share of a cell's UMIs from mitochondrial genes; high in damaged cells |
| Doublet score | Scrublet's measure of similarity to simulated doublets |
| Q30 | Base quality ≥ 30, i.e. error probability ≤ 0.1% |
| AnnData | Python container for an annotated matrix (X, obs, var, obsm, layers, uns) |
| HDF5 / .h5 / .h5ad | Hierarchical binary format; Cell Ranger matrix file; saved AnnData object |
| Sparse matrix (CSR/CSC) | Storage of only non-zero values; row- or column-oriented |
| Categorical variable | Column storing repeated labels once, with integer codes per row |
| scverse | Ecosystem of Python single-cell tools built around AnnData and scanpy |

## Further reading

- [scanpy documentation and tutorials](https://scanpy.readthedocs.io)
- [anndata documentation](https://anndata.readthedocs.io)
- [scverse ecosystem](https://scverse.org/packages/)
- [Lun et al., 2019 — EmptyDrops](https://doi.org/10.1186/s13059-019-1662-y)
- [Wolock et al., 2019 — Scrublet](https://doi.org/10.1016/j.cels.2018.11.005)
