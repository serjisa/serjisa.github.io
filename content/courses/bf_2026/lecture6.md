---
lang: en
title: Lecture 6
permalink: /bf.msu.2026/lecture6/
---
# Lecture 6. Visualizing single-cell data: PCA space, t-SNE and UMAP

Lecture 5 ended with the standard recipe: normalize, log-transform, scale, PCA. This lecture is about what comes next: how to use the PCA representation, and how to look at it with two-dimensional visualizations (t-SNE, UMAP) — what they show and, more importantly, what they don't. The practical part runs the full pipeline in scanpy, from QC to UMAP, on a PBMC dataset from three donors.

## 1. The working matrix: PCA space

After normalization, log transform and PCA, each cell is described by \~20–50 principal components (`adata.obsm["X_pca"]`). This is the **"good" matrix**, and the one to use for downstream analysis: clustering, trajectory inference, and any statistic you want to compute on cell similarity.

- Distances between cells in PC space approximate distances in log-normalized expression space, restricted to the directions where the data really vary.
- The discarded components contain mostly noise, so PC space is both smaller and cleaner than the full gene space.

**How many PCs.** As discussed in Lecture 5, cell states vary along far fewer directions than there are genes: typically fewer than \~20–30. So the exact number of PCs matters little. Results with 20, 30 or 50 PCs (or even all genes) look nearly the same. Too few (e.g., 5) is a problem: genuinely different subpopulations merge. Formal procedures for choosing the number of PCs (elbow plots and the like) rarely change conclusions; a value in the 20–50 range is standard.

## 2. Why visualize, and the problem with 30 dimensions

Clustering and other analyses can run in 30 dimensions without ever being visualized. But looking at data matters. The human brain is very good at spotting patterns (sometimes too good, seeing patterns that aren't there).

- A useful rule when developing a method or testing an idea: find a visualization in which the effect should be visible. If you cannot see it by eye, it is quite likely not there. The converse does not hold: seeing a pattern doesn't prove it is real.
- Visualization is a tool for generating hypotheses, which you then test rigorously. "It looks like this on the plot" is not an argument in a paper.

The problem is that we can think in three, at most four, dimensions, not thirty. Plotting just PC1 vs PC2 often hides structure: clusters that are well separated in 5 or 30 dimensions can overlap in two linear dimensions. So we need non-linear methods that compress the 30-dimensional space into 2D while keeping the properties we care about most.

## 3. Manifolds and neighbour-preserving embeddings

Not all properties of a 30-dimensional dataset can be kept in 2D. The choice made by t-SNE and UMAP: **keep small (local) distances, give up large (global) ones**.

Intuition: imagine points lying on a ribbon curled up in 3D. What matters is that neighbouring points form a continuous ribbon, not that two far-apart parts of the ribbon happen to be closer in 3D than two other parts. In 2D we'd like to see the ribbon unrolled into a flat strip.

Mathematically, such data lie on a **manifold**: a space that looks flat (linear) when you zoom in on any small region. The Earth is a sphere, but locally it looks flat, which is why flat maps of small regions work. Manifold-learning methods look at each point's **local neighbourhood** and try to place the same neighbours next to each other in 2D. What is lost is the relationship between distant regions.

## 4. How t-SNE works

**The spring analogy.** Connect each point to its nearby points with springs, strong for close neighbours and weak for distant ones. Then press the whole system flat onto a table (points may pass through each other) and let it settle into equilibrium. Points that were strongly connected end up close together; for points that were far apart, it hardly matters where they land.

**More precisely:**

1. **Affinities in the original (PCA) space.** For each point, similarities to other points are computed with a Gaussian kernel. Its width is chosen per point so that each point has a fixed effective number of neighbours (the **perplexity**, typically 30). Dense and sparse regions are therefore treated alike.
2. **Affinities in 2D.** In the embedding, similarities are computed with a **Student's t-distribution** (one degree of freedom, i.e. a Cauchy kernel).
3. **Optimization.** Starting from an initial layout, points are moved iteratively so that the 2D affinities match the original ones (minimizing the KL divergence).

**Why the t-distribution.** Its predecessor, SNE, used a Gaussian in 2D as well. The t-distribution has **heavier tails** than the Gaussian. This allows moderately dissimilar points to be placed far apart in 2D, which relieves the "crowding problem" (there isn't enough room in 2D for all moderately-distant neighbours). As a result, t-SNE produces clearly separated clusters.

**The consequence.** Far apart and very far apart look almost the same to t-SNE, while close vs far matters a lot. So local neighbourhoods are kept, and clusters become visually obvious, but the arrangement of distant clusters relative to each other is largely arbitrary.

## 5. UMAP, and how it relates to t-SNE

UMAP (McInnes, Healy & Melville, arXiv 2018) was presented in very different language: topological data analysis, fuzzy simplicial complexes, Riemannian geometry. It was claimed to preserve local structure as well as t-SNE and *more global structure*. An influential 2019 *Nature Biotechnology* paper (Becht et al.) repeated this claim for single-cell data, and UMAP quickly became the default.

Later work showed that the difference is much smaller than it looked:

- **Global structure comes from initialization.** Original t-SNE starts from a random layout, so the final positions of distant clusters relative to each other are arbitrary. UMAP starts from a *spectral embedding* of the kNN graph (Laplacian eigenmaps — roughly, a PCA-like decomposition of the graph), which already contains a sensible global layout. Optimization mostly refines local structure and doesn't scramble the clusters, so some global structure survives. t-SNE initialized with PCA preserves global structure about as well (Kobak & Linderman, *Nat. Biotechnol.* 2021).
- **Cluster compactness comes from the balance of forces.** All these methods combine attraction between kNN-graph neighbours with repulsion between all points. UMAP behaves like t-SNE with **stronger attraction**: running t-SNE with the *exaggeration* parameter raised (to about 4) gives UMAP-like embeddings, because UMAP's sampling-based optimization effectively weakens repulsion (Böhm, Berens & Kobak, *JMLR* 2022). Increasing attraction further gives layouts like ForceAtlas2 and, in the limit, Laplacian eigenmaps.

So the intuitions in this lecture apply equally to t-SNE and UMAP; conceptually they are close relatives. Other methods in the same family include force-directed graph layouts (ForceAtlas2, SPRING — the spring intuition literally) and spectral methods (Laplacian eigenmaps, diffusion maps).

A practical difference: modern implementations of both work from a **kNN graph** rather than from all pairwise distances (for t-SNE this is an approximation that works because the affinities of distant points are near zero). In scanpy, UMAP is computed from the graph built by `sc.pp.neighbors`.

## 6. What t-SNE and UMAP do not preserve; parameters and pitfalls

**Cluster sizes and spread are not meaningful.** Each point's neighbourhood is normalized to look alike (perplexity in t-SNE, a per-point bandwidth in UMAP), so a tight cluster and a diffuse cluster in the original space can come out looking the same. The apparent size of a cluster on the plot mostly reflects **how many cells** it contains, not how heterogeneous they are. A large, spread-out island is not evidence of high transcriptional diversity; a small compact one can actually have higher within-cluster variance. (Variants such as densMAP try to retain density information.)

**Distances between clusters are not meaningful.** "These two clusters are closer on the UMAP, so they are more similar" is not a valid inference.

**What is preserved** is, approximately, who is neighbour to whom: the local structure of the manifold.

**A safe rule.** If you are not sure which properties a UMAP preserves, do not compute anything on UMAP coordinates. Use it to look at the data and generate hypotheses; compute statistics, clustering and distances in PCA space. Reporting a statistic computed on PCA is standard; reporting one computed on UMAP coordinates will (rightly) draw criticism. Much of the controversy about UMAP in the field (e.g., Chari & Pachter, *PLoS Comput. Biol.* 2023) came from exactly such over-interpretation. Used as a visualization, UMAP remains very informative.

**Input.** UMAP is usually computed on the PCA representation, not on all genes. The result is very similar either way, but since downstream analysis uses the PCs, it is more consistent to visualize the same space.

**Number of PCs.** UMAPs from 20, 30, 50 PCs or the full matrix look nearly identical, consistent with data on a manifold of fewer than \~20–30 dimensions. With 5 PCs, distinct subclusters merge.

**Number of neighbours** (`n_neighbors`). Typically 15–30 (scanpy default 15, Seurat 30). Very small values make the embedding reflect only the most local structure and produce artifacts. Within a reasonable range, results change little.

**`min_dist`** (and `spread`). UMAP's original parameters *a* and *b* shape the low-dimensional similarity kernel; implementations derive them from the user-facing `min_dist` and `spread`. `min_dist` controls how tightly points pack: 0.1 gives very compact clusters, 0.5 looser blobs. Defaults differ: 0.5 in scanpy, 0.3 in Seurat — one reason the same data can look slightly different in the two. Choose whatever reads best; it is a visual setting.

**Spurious clusters.** With aggressive settings (strong attraction, few neighbours), these methods can split pure noise into convincing-looking clusters. On simulated data with no structure at all, random fluctuations get amplified into islands. Be very cautious about interpreting small separated groups.

**Clustering is not done on UMAP.** Clustering is done in PCA space — in practice on the kNN graph built from PCA (next lecture).

## 7. Practical: setup, notebook hygiene, and what is in `adata.X`

The practical runs in Google Colab (a GPU runtime is needed only for the GLM-PCA step at the end).

**Notebook hygiene.** Part of the final assessment is an analysis notebook. Delete outputs that don't help the reader (pip install logs, verbose messages); keep the plots and tables that tell the story. A notebook is read by people, not just executed.

**Imports and settings.** numpy, pandas, matplotlib/seaborn, and **scanpy** (`sc`), the main analysis library. `sc.settings.verbosity` sets how much functions report about what they changed. Colab machines usually have two CPU cores; limiting parallel jobs to 2 (`sc.settings.n_jobs = 2`) avoids errors from functions trying to use more cores than available.

**AnnData recap.**

- `adata.X` — the expression matrix (cells × genes), the core of the object.
- `adata.obs` / `adata.var` — data frames describing cells and genes.
- `adata.obsm` — low-dimensional representations of cells (PCA, t-SNE, UMAP).
- `adata.obsp` — cell × cell matrices, i.e. **graphs**. A graph (vertices connected by edges) can be stored as an adjacency matrix: nonzero entries are edges, and in a weighted graph the values are the weights. Sparse matrices make this cheap. The kNN graph lives here. `adata.varp` is the gene × gene equivalent (e.g., gene graphs for finding modules).

**The dataset.** PBMCs (peripheral blood mononuclear cells) from **three donors**, loaded from an `.h5ad` file with `sc.read_h5ad`. Pre-existing annotations are removed. The donor structure matters later in the practical.

**Always check what `adata.X` contains.** Downloaded objects may hold raw counts, depth-normalized values or log-normalized values, and many functions assume one of these.

- Look at a few values, or simply the maximum. Integers (e.g., a maximum of 8311) → raw counts. Normalization or a log transform would essentially never produce only integers.
- Non-integer values: compute per-cell sums. All cells summing to the same number → depth-normalized but not log-transformed. Unequal sums (and a small maximum, typically below \~10) → log-transformed.
- Don't convert a large sparse matrix to dense just to inspect it.

## 8. Practical: QC, doublets, and keeping the raw counts

**QC metrics.** Flag mitochondrial genes (`adata.var["mt"] = adata.var_names.str.startswith("MT-")`) and call `sc.pp.calculate_qc_metrics(adata, qc_vars=["mt"], inplace=True)`. It adds genes per cell, counts per cell and percent mitochondrial counts to `adata.obs` — the metrics computed by hand in Lecture 4. Plot their distributions and set thresholds. Here the authors had already filtered most low-quality cells; additional cuts (about 12% mitochondrial, a minimum of \~700 genes) remove a small tail of cells that would otherwise add noise to clustering.

**Doublets.** Run Scrublet (`sc.pp.scrublet`) **after** removing low-quality cells but **on raw counts, before any normalization or log transform**. It adds `doublet_score` and `predicted_doublet` to `adata.obs`. Here we don't filter on them yet, to see later how doublets look in the embedding.

**Sparsity.** Fewer than 10% of matrix entries are nonzero.

**Keep the raw counts.** After normalization and log transform, the counts in `adata.X` are gone, but some methods need them. Differential expression methods based on negative binomial regression (e.g., DESeq2 or edgeR on pseudobulk) model integer counts and expect them as input. Save a copy before transforming, either as a separate object (`adata_raw = adata.copy()`) or in a layer (`adata.layers["counts"] = adata.X.copy()`).

**Why `.copy()`.** In Python, `b = a` does not copy an object; both names point to the same object in memory, so modifying `b` changes `a`. With AnnData, forgetting `.copy()` means your "raw" object gets normalized along with the main one. This is a common and easy-to-miss bug.

## 9. Practical: distributions, normalization, log transform, highly variable genes

**Count distributions of single genes.** *MALAT1*, a very highly expressed long non-coding RNA, has a broad distribution of large counts. *CD4* is mostly zeros, with occasional 1s and 2s. The *CD4* picture is the typical one, consistent with a negative binomial with a small mean.

**Mean–variance plot.** For every gene, plot log10(variance) against log10(mean). At low means, variance ≈ mean (Poisson-like). At higher means, variance grows much faster: overdispersion. Two components add up here: the technical gamma–Poisson variability from Lecture 5, and real biological differences between cells. Genes whose variance lies clearly **above the overall trend** vary more than the null model predicts, and these are the biologically interesting ones. Selecting them is the idea behind **highly variable genes**.

**Normalization.** Divide each cell's counts by its total and multiply by a common target. Here the target is the median total count (≈5,493), so a typical cell keeps its scale (`sc.pp.normalize_total`; with no target given, it uses the median). After scaling, counts are no longer integers. For a low-expression gene such as *CD14*, the histogram (with a log y-axis) shows separate bumps around what were 1, 2, 3 counts, smeared by different scale factors, which merge at higher values.

**Log transform.** `sc.pp.log1p` computes ln(x + 1). After it:

- *MALAT1* looks roughly normal (with some real heterogeneity).
- *CD4* does not: a spike at zero plus separate bumps inherited from the 1-, 2-, 3-count groups. This is the low-count artifact from Lecture 5. The spike at zero is often misread as "zero inflation" or "dropouts", but it is what a negative binomial with a small mean looks like after the log.
- On the mean–variance plot, the dependence is still there but much weaker. Before the log, a handful of very highly expressed genes had variances orders of magnitude larger than the rest; on a linear scale they would account for almost all the variance in the dataset. After the log, no small group of genes dominates. This is why even clustering on log-normalized expression works reasonably.

**Don't run in-place transformations twice.** `normalize_total` and `log1p` overwrite `adata.X`. Re-running the cell silently normalizes and logs already-transformed data — no error, just nonsense. Accidentally re-running a cell is common. If in doubt, start again from the saved raw counts; these steps take seconds. By contrast, re-running `sc.tl.umap` is harmless: it reads the kNN graph without modifying it and just overwrites the UMAP coordinates.

**Highly variable genes.** `sc.pp.highly_variable_genes(adata, n_top_genes=3000)` models how variability depends on mean expression and ranks genes by how far they exceed the trend. It adds columns to `adata.var`: `highly_variable`, mean, dispersion (NaN for genes with zero counts everywhere). On the mean–variance plot, many selected genes have low or medium expression; the most highly expressed genes are often *not* highly variable relative to their mean. (A `batch_key` option, here for the donor, will be explained next lecture.)

## 10. Practical: scaling, PCA, kNN graph, UMAP, batch effects, GLM-PCA

**`adata.raw` and subsetting.** Store the log-normalized expression of all genes in `adata.raw = adata` (used later, e.g., for plotting any gene). Then subset the main object to the 3,000 HVGs. Scaling makes the matrix dense, so restricting to HVGs saves a lot of memory.

**Scaling.** `sc.pp.scale(adata, max_value=10)` z-scores each gene (mean 0, SD 1). Zeros become negative values, which is why the matrix becomes dense. `max_value=10` clips values more than 10 SD from the mean. PCA minimizes *squared* distances, so a few extreme outliers can pull a component toward themselves; clipping is a simple safeguard. Good datasets have few such outliers; bad ones may have many.

**PCA.** `sc.tl.pca(adata, n_comps=30)` stores the cell embedding in `adata.obsm["X_pca"]` — the 30-dimensional working representation.

**PC1 vs PC2 colored by marker genes** shows where the main PBMC populations are:

- *CD3E* — T cells
- *NKG7* — NK cells and cytotoxic CD8 T cells
- *CD19* (or *MS4A1*) — B cells
- *CD14* — classical (CD14+) monocytes
- *FCGR3A* (encodes CD16) — CD16+ NK cells and non-classical (CD16+) monocytes

Even two PCs separate the main populations reasonably, but UMAP shows the structure in more detail.

**kNN graph and UMAP.** `sc.pp.neighbors(adata)` builds the kNN graph on the PCs and stores it in `adata.obsp` (distances and connectivities). `sc.tl.umap(adata, min_dist=0.3)` lays it out. A kNN graph keeps only distances to each cell's k nearest neighbours and discards everything else. It is a discrete approximation of the manifold: once you work with the graph, you have committed to local structure only.

**Batch effect.** Coloring the UMAP by donor shows that cells of the same type split by donor. Without that coloring, you would likely call these separate clusters. The split is not a UMAP artifact: UMAP was computed from the PCs, so the separation is present in PCA space too. This donor-driven variation is a **batch effect**, the topic of the next lecture.

**Doublets on the UMAP.** Color by `doublet_score`. Small groups of cells with uniformly high scores, often sitting between two cell types, are likely doublet clusters and can be removed (before or after this step). Here there is no dramatic case.

**Markers on the UMAP** (`sc.pl.umap(adata, color=[...])`) identify T cells, CD8 T and NK cells, B cells, CD14 and CD16 monocytes. The cell-type structure is now overlaid with donor structure.

**GLM-PCA.** Normalize–log–scale–PCA is a workaround for PCA's implicit Gaussian assumption. **GLM-PCA** instead fits a low-rank model with a count likelihood (Poisson here; NB is also possible) directly to the **raw count matrix**. It has no closed-form solution and must be fitted by iterative optimization. Classic implementations take hours on a typical dataset, while the standard pipeline takes seconds — one reason GLM-PCA isn't the default. Faster algorithms exist: fastglmpca (Weine, Carbonetto & Stephens, *Bioinformatics* 2024) is an R package; the practical uses a Python/PyTorch implementation that runs on GPU and keeps the matrix sparse, finishing in minutes.

The GLM-PCA embedding looks different from the PCA one, but the kNN graph and UMAP built on it look very similar to the standard pipeline's; the donor separation is, if anything, more pronounced. For typical data, GLM-PCA gives little benefit. It is most worth considering when total counts per cell are very low, where log-transform artifacts are worst.

```python
import scanpy as sc

adata_raw = adata.copy()                       # keep raw counts
sc.pp.normalize_total(adata)                   # target = median total counts
sc.pp.log1p(adata)
sc.pp.highly_variable_genes(adata, n_top_genes=3000)
adata.raw = adata                              # log-normalized, all genes
adata = adata[:, adata.var.highly_variable].copy()
sc.pp.scale(adata, max_value=10)
sc.tl.pca(adata, n_comps=30)
sc.pp.neighbors(adata)                         # kNN graph on PCs
sc.tl.umap(adata, min_dist=0.3)
sc.pl.umap(adata, color=["donor", "doublet_score", "CD3E", "CD14"])
```

## 11. Key points

- The cells × \~30 PCs matrix is the working representation for clustering, trajectories and statistics. The exact number of PCs (20–50) rarely matters; too few merges real populations.
- t-SNE and UMAP compress this space to 2D by preserving **local neighbourhoods** and giving up global geometry.
- On t-SNE/UMAP plots, **cluster sizes, spreads and between-cluster distances are not interpretable**. Use them to look and generate hypotheses; compute on PCA.
- UMAP ≈ t-SNE with stronger attraction; its better global layout comes mostly from spectral initialization.
- Aggressive parameters can create clusters out of noise.
- In practice: check what `adata.X` contains; run Scrublet on raw counts; keep a copy of the counts; never re-run in-place transformations; color the UMAP by donor/batch and doublet score before interpreting clusters.

## Glossary

| Term | Meaning |
| --- | --- |
| Manifold | A space that looks flat when you zoom into any small region; cells are thought to lie on a low-dimensional manifold inside expression space |
| Neighbour embedding | Family of methods (t-SNE, UMAP, ForceAtlas2) that place kNN-graph neighbours close together in 2D |
| Perplexity | t-SNE setting for the effective number of neighbours per point |
| Exaggeration | t-SNE factor that multiplies attractive forces; higher values give more compact, UMAP-like clusters |
| kNN graph | Graph connecting each cell to its k nearest neighbours; an approximation of the manifold |
| `min_dist` | UMAP setting for how tightly points pack in 2D |
| Highly variable genes | Genes whose variance exceeds what the mean–variance trend predicts |
| Batch effect | Variation driven by sample, donor or processing rather than biology of interest |
| GLM-PCA | PCA-like decomposition with a count (Poisson/NB) likelihood, fitted on raw counts |

## Further reading

- van der Maaten & Hinton (2008). Visualizing data using t-SNE. *JMLR* 9:2579–2605.
- McInnes, Healy & Melville (2018). UMAP: Uniform Manifold Approximation and Projection. arXiv:1802.03426.
- Kobak & Berens (2019). The art of using t-SNE for single-cell transcriptomics. *Nat. Commun.* 10:5416.
- Kobak & Linderman (2021). Initialization is critical for preserving global data structure in both t-SNE and UMAP. *Nat. Biotechnol.* 39:156–157.
- Böhm, Berens & Kobak (2022). Attraction-repulsion spectrum in neighbor embeddings. *JMLR* 23(95):1–32.
- Chari & Pachter (2023). The specious art of single-cell genomics. *PLoS Comput. Biol.* 19:e1011288.
- Townes et al. (2019). Feature selection and dimension reduction for single-cell RNA-seq based on a multinomial model. *Genome Biol.* 20:295.
- Weine, Carbonetto & Stephens (2024). Accelerated dimensionality reduction of single-cell RNA sequencing data with fastglmpca. *Bioinformatics*.
