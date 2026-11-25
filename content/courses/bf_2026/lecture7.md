---
lang: en
title: Lecture 7
permalink: /bf.msu.2026/lecture7/
---
# Lecture 7. Batch effects and batch correction

Lecture 6 ended with a problem. In the PBMC dataset from three donors, cells of the same type split by donor on the UMAP, and the split was already present in PCA space. This lecture is about that problem: analysing several samples together, and **batch effects**, systematic differences between samples that we don't want to see. In code, batch correction is again only a line or two. Conceptually, though, it differs from everything so far.

In Lectures 5–6 each step rested on a clear statistical model (Poisson and negative binomial noise, PCA as the best low-rank approximation), and the choice between reasonable methods rarely changed the result. Batch correction has no such model. We see an effect we don't want, but we can't fully say which part of it we want to remove. Different methods make different assumptions, results depend on the method and its parameters, and there is no single recommendation. What this lecture gives instead is a set of mechanisms, failure modes and practical hints for choosing between them.

## 1. Several samples: the batch effect

Building a UMAP and clusters is rarely a scientific goal in itself. Sometimes the goal is to characterize the cell types in a tissue (e.g., an unusual tumour whose composition is unknown). More often it is a comparison, and comparisons need several samples: several patients, the same patient before and after chemotherapy, healthy donors vs patients, controls vs an experimental treatment. The question is then how the condition changes the cells: their composition (e.g., the immune microenvironment), their states, their response.

**The naive approach** is to concatenate the cells × genes matrices from all samples and analyse them as one. Some steps are naturally done per sample first:

- **QC and removal of empty droplets**, because cell quality and the ambient profile depend on the sample.
- **Doublet detection**, because doublets form within one channel of the 10x chip. Cells from samples loaded into different channels can't share a droplet. (The exception is multiplexed designs, where several samples are pooled into one channel and later separated by hashtags or genotype. There, doublets between samples do occur, and are in fact easy to detect.)

After that, the matrices are merged and processed together.

**What goes wrong.** You saw a mild version in Lecture 6, where PBMCs split by donor. In extreme cases, cells split almost completely by sample: cells from two patients occupy separate regions of the UMAP with almost no overlap, even though both samples contain the same cell types. Not every dataset shows it this strongly, but such cases do occur in real data. The same phenomenon was already known from bulk RNA-seq; in single-cell data it is far more visible.

**Terminology.** A **batch** is literally a lot or a set of things processed together. For now we treat "batch" and "sample" as the same thing. In general a batch is any group of cells that shares technical conditions (processed on the same day, in the same channel, with the same protocol), and one batch can contain several samples or vice versa. The systematic difference between batches is the **batch effect**.

## 2. Where differences between batches come from

**Biological differences.** Some differences between samples are real and expected.

- **Individuals differ.** No two people have identical expression profiles: genetics differs, and even identical twins differ epigenetically.
- **Karyotype.** Cells with an XX karyotype express *XIST*, the long non-coding RNA that silences one of the two X chromosomes (X inactivation). Without it, XX cells would have twice the X-linked expression of XY cells. XY cells don't express *XIST* but do express Y-chromosome genes absent from the X (e.g., *RPS4Y1*, *DDX3Y*). *XIST* and these Y genes are the easiest way to check the karyotype of a sample in the data. (Edge cases exist: *SRY*, the sex-determining gene on the Y, lies outside the pseudoautosomal regions that recombine between X and Y, but it can be translocated to the X by error in paternal meiosis. This produces individuals with an XX karyotype, X inactivation and a male phenotype.)
- **Species.** Comparing, e.g., mouse and human cells brings large evolutionary differences in expression.

If only biology differed, there would be little problem. The trouble is that technical differences come on top.

**Technical differences.**

- **Cell quality.** In one sample the cells were isolated better than in another.
- **Storage and sample preparation.** Sometimes a biopsy goes from the operating table straight to the single-cell facility; sometimes it has to be frozen and processed days later. Dissociation protocols may also differ (Lecture 2).
- **Sequencing depth.** Even this alone creates a batch effect. Take one sample and randomly subsample its counts to create a "shallower" copy. Normalization by depth should remove the difference in the limit of large counts, but many genes have counts like 0, 1, 2. Subsampling turns some 1s into 0s, and no scale factor turns a 0 back into a 1. Lowly expressed genes partly vanish from the shallower copy, and this is a systematic difference between the two "batches".

## 3. Interesting vs uninteresting variation

**Why the batch effect is a problem.** We know its cause, so why not simply live with it? Because of interpretation. When two clusters appear, we need to know whether they are two different cell types, or one cell type coming from two samples. This is the central, and the hardest, question of the lecture: is a given piece of heterogeneity in the embedding the variation we are interested in, or variation we are not?

The split is deliberately not "biological vs technical". Some biological variation is real but irrelevant to the question. *XIST* expression differs between XX and XY donors for real biological reasons, yet in most studies nobody wants cells to cluster by karyotype. **Batch correction methods** are methods that remove the part of the variation we are not interested in. Because "not interested" depends on the question, there are many methods with different assumptions and logic.

**What counts as uninteresting depends on the question.**

- **Immune microenvironment of tumours.** The goal is usually clear: CD8 T cells from all patients should end up in one cluster, so that heterogeneity *within* CD8 T cells (activation, exhaustion, response to immunotherapy) can be studied across patients.
- **The tumour cells themselves.** Here it is much less clear. Paraphrasing Tolstoy: all happy families are alike, every unhappy family is unhappy in its own way — and every cancer is different. Two patients with the same diagnosis (e.g., stage IIIA lung adenocarcinoma) and even the same driver mutation (*KRAS* or *EGFR*) still carry many different passenger mutations, because selection acts differently in a tumour than in normal tissue. So should the malignant cells of different patients be integrated or kept apart?
  - In a 2019 single-cell study of **follicular lymphoma**, the malignant B cells of each patient formed their own cluster, and the authors left them that way: these really are different populations, and intratumour heterogeneity was not the main interest.
  - In **glioblastoma** the opposite is true. Glioblastoma is a glial brain tumour with very poor prognosis (median survival is around 15 months even with treatment). It infiltrates the brain tissue and is highly plastic: malignant cells move between a small number of shared states (e.g., mesenchymal-like and astrocyte-like). To study these states and compare their proportions between patients, the malignant cells of different patients have to be brought into a common space.

The choice is task-specific, and there is no general recipe.

## 4. The simplest step: selecting highly variable genes within each batch

Recall (Lecture 6) that the variance of a gene grows with its mean in a predictable way: Poisson-like at low means, overdispersed (negative binomial) at higher means. **Highly variable genes** (HVGs) are those whose variance is clearly above this trend, because on top of technical noise they vary biologically: they are high in some cells and low in others. Only HVGs are used to build the embedding.

**The trick:** select HVGs within each batch separately, then combine the lists. Take two batches, one from an XX donor and one from an XY donor. If HVGs are selected on the merged data, *XIST* looks highly variable: it is on in half of the cells and off in the other half. Within each batch, though, *XIST* is uniformly on (or uniformly off), and only technical noise remains. So it is not selected. In general, genes that are stable within batches but differ systematically between them drop out, and genes describing heterogeneity within batches stay.

**Union or intersection.** Taking the intersection keeps genes variable in every batch; the union keeps genes variable in at least one batch. The union is usually the better choice, because a cell type, and its markers, may be present in only some batches. In scanpy this is the `batch_key` option mentioned in Lecture 6: `sc.pp.highly_variable_genes(adata, batch_key="donor")` selects HVGs per batch and ranks genes by the number of batches in which they are highly variable.

**Why this is not enough.** Genes that drive the batch effect are often also interesting. Consider again the batch created by depth alone. Suppose a lowly expressed gene is a marker of one cell population. It is genuinely highly variable within each batch, so it is selected. But in the shallower batch its counts often drop to zero, so it also differs systematically between batches. HVG selection per batch is therefore standard practice, but on its own it rarely removes the batch effect.

## 5. Three levels at which a batch effect can be removed

The pipeline has three main objects:

1. the **expression matrix** (cells × genes);
2. the **embedding** (e.g., PCA);
3. the **kNN graph** built on the embedding. Clustering today is done mostly on this graph rather than directly in PCA space (Lecture 8), and UMAP is drawn from it.

A batch effect present at one level propagates to everything downstream: if it is in the expression matrix, it will be in the PCA and in the graph. So it can be removed at any of the three levels, and correction methods fall into three classes:

- build the **graph** in a batch-aware way, leaving the expression and the embedding as they are;
- build a corrected **embedding**, so that the graph, clustering and UMAP built from it are corrected;
- correct the **expression values** themselves, and rerun the whole pipeline on them.

We go through them from the simplest.

## 6. Graph level: BBKNN, and the two failure modes

**BBKNN (batch-balanced k-nearest neighbours).** In an ordinary kNN graph, each cell is connected to its k nearest cells, whatever their batch. In BBKNN each cell is connected to its nearest neighbours **in each batch separately**. With three batches and one neighbour per batch, each cell still gets three edges, but one goes to each batch. The graph thus forcibly connects cells across batches, and clustering and UMAP built on it no longer split by batch. The PCA space itself is not changed and still contains the batch effect.

BBKNN is one of the earliest and simplest methods. It is fast and convenient in Python, but it is rarely the method of choice now. It is, however, the easiest way to see how batch correction can fail. It relies on an assumption: the nearest cell in another batch is the true counterpart of a cell. This often fails in two ways.

**Failure 1: the batches are shifted.** Imagine one cell population in 2D, present in both batches, but batch 2 is shifted horizontally relative to batch 1. The right correction is simply to shift batch 2 back. With BBKNN, though, every cell of batch 1 finds its cross-batch neighbours in the edge layer of batch 2 that faces it, and vice versa. Cells deeper inside each cloud never get connected to their real counterparts. The two clouds are pulled together but remain side by side, rather than overlapping.

**Failure 2: different composition.** Suppose both batches share cell type A, batch 1 also has type B, and batch 2 has type C. A cell of type B must find neighbours in batch 2. If they are A cells, the damage is limited. But often the closest cells are C, and then two unrelated cell types get merged.

These are the two artifacts that every batch correction method can produce:

- **Undercorrection** (under-integration): part of the uninteresting variation remains (Failure 1).
- **Overcorrection** (over-integration): part of the interesting variation is removed, e.g., two different cell types are merged (Failure 2).

Methods can be placed along an axis from more prone to undercorrection to more prone to overcorrection, and every method can produce both. BBKNN is prone to both.

## 7. Mutual nearest neighbours (MNN)

Most batch correction methods are built on one idea that filters the cross-batch neighbours: **mutual nearest neighbours**. A pair of cells from two batches is kept only if each is among the other's k nearest neighbours.

**Why this helps.** In BBKNN every cell is forced to have cross-batch neighbours, even a cell with no real counterpart in the other batch. Its edges are typically one-sided: the cell it points to has better matches elsewhere, so the pair isn't mutual and is dropped. Mutual pairs tend to form between cells that really correspond, so MNN can be seen as a clean-up of the kNN graph that removes one-sided edges. It reduces overcorrection but doesn't eliminate it: if two unrelated types B and C are each other's best matches, MNN will still pair them.

**From pairs to a correction.** MNN pairs also fix the shifted-batches problem (Failure 1), once they are used as **anchors** rather than as edges. The difference vectors between paired cells estimate how one batch is displaced relative to the other. That displacement is then smoothed and applied to *all* cells, not only to the paired ones. So even though the pairs come from the facing edges of the two clouds, the whole cloud is shifted onto its counterpart.

Conos uses this idea to build a joint graph across samples. Other methods use MNN pairs as anchors for correcting the embedding or the expression values (Sections 8–9). The original MNN correction method (Haghverdi et al., 2018) estimates correction vectors from such pairs.

## 8. Embedding level: Scanorama and Harmony

If the embedding is corrected, everything built from it (graph, clustering, UMAP) is free of the batch effect.

**Scanorama** (Hie et al., 2019) works like stitching photos into a panorama. It reduces each dataset to a low-dimensional space, finds mutual nearest neighbours between all pairs of datasets, and uses them to merge the datasets into a common embedding. It performed well in early benchmarks and is easy to use in Python, but it is less widely used in practice than Harmony.

**Harmony** (Korsunsky et al., 2019) is one of the most widely used methods and a reasonable default; in practice it usually removes batch effects well. Unlike most methods, it is not based on MNN. The intuition is the one you would follow by eye: "this cluster of batch 1 probably corresponds to that nearby cluster of batch 2, so let's move them onto each other."

1. **Cluster.** Harmony takes an embedding (usually PCA) and clusters the cells coarsely. The clusters are soft (each cell belongs to several with different weights), and the clustering is penalized for clusters dominated by one batch, which pushes it toward clusters that mix batches.
2. **Correct within clusters.** Within each cluster, Harmony computes the centroid of each batch and moves the cells of each batch so that the batch centroids coincide.
3. **Repeat.** After the move, the clustering may change, so Harmony clusters again, corrects again, and so on, until the result stops changing (convergence).

Each correction step is linear within a cluster, but because cells are moved by different amounts in different clusters and the clustering changes between iterations, the overall transformation is non-linear.

**Input.** Harmony and the other methods do not require PCA as input. They need a good embedding, whatever it is. For example, single-cell ATAC-seq (a method measuring open chromatin) is usually embedded with LSI (latent semantic indexing), and Harmony can correct that.

**Convergence as a diagnostic.** Harmony's logic assumes that the coarse clusters correspond to the same cell populations across batches. If that is true, the clustering stabilizes after a few iterations. If the clustering keeps changing from iteration to iteration and the algorithm fails to converge, the assumption is probably violated: for example, a cell type in one batch lies closer to a different cell type in another. Fast convergence suggests a stable correction; a run that keeps going to its iteration limit is a warning sign. Then try changing the input or combining methods.

**Sensitivity.** Unlike UMAP, where 20 or 50 PCs give nearly the same picture, Harmony's result can change noticeably with the number of PCs it receives, because of the iterative clustering.

## 9. Expression level: Seurat anchors

The third option is to correct the expression values themselves, after which the whole pipeline (PCA, graph, clustering, UMAP) is rerun on corrected data. The classic example is **Seurat v3 integration** (Stuart et al., 2019), built on mutual nearest neighbours.

1. **Find anchors.** Seurat looks for mutual nearest neighbours between two batches, which it calls **anchors**. It finds them not in PCA space but in a space from **canonical correlation analysis (CCA)**. CCA finds directions that are maximally correlated between the two datasets, i.e., the shared structure, so neighbours found there are less affected by the batch effect.
2. **Compute correction vectors.** Each anchor pair gives a difference vector between the two batches.
3. **Extrapolate and correct.** These vectors are weighted and extended to all cells, including those without an anchor. For example, if cells of two cell types in batch 2 are displaced "downward" relative to batch 1, a third type is assumed to be displaced in the same way. The expression of the second batch is then corrected toward the first.

This requires one dataset to serve as a **reference** that others are corrected to (or a common average). Newer Seurat versions perform integration in a low-dimensional space (e.g., the PCA space) rather than on the full expression matrix, but the logic of anchors and correction vectors is the same.

**A caution.** Corrected expression values are fine for visualization and clustering, but they are no longer counts and are not independent measurements. For differential expression, use the original counts with batch included in the statistical model, not the corrected values.

## 10. Choosing a method

Systematic benchmarks of batch correction exist (e.g., Tran et al., 2020; Luecken et al., 2022). Some methods are clearly worse on average than others, but there is no universal winner: whether Seurat or Harmony works better depends on the dataset, and the packages keep changing. More fundamentally, there is no agreed definition of what a batch effect *is*, so any benchmark rests on a subjective choice of what should and should not be merged.

A practical approach:

- Start with the method you know best and can run well in your ecosystem. In practice the choice is limited by language: Python users work mainly with scverse tools (BBKNN, Scanorama, Harmony via harmonypy, scVI), R users with Seurat. Converting objects to run a method from the other ecosystem is possible, but people do it only when nothing else works.
- Check the result for **undercorrection** (cells of the same type still split by batch) and **overcorrection** (distinct cell types merged, known markers no longer separating populations).
- If it looks reasonable, continue. If it is clearly wrong, try another method or combine methods.
- Expect sensitivity to inputs and parameters, and check that your conclusions don't depend on them.

In earlier steps of the pipeline, ten reasonable choices gave essentially the same result. Here they don't, and the decision inevitably relies on biological knowledge of what should and should not be separate.

## 11. Key points

- When several samples are analysed together, cells often split by sample. Part of this is biology (individuals, karyotype, species), part is technical (cell quality, storage, preparation, sequencing depth).
- Batch correction removes variation we are not interested in. What that is depends on the question, so there is no single correct method.
- QC and doublet detection are done per sample; HVGs are best selected per batch (union), which helps but rarely suffices.
- Correction can act on the graph (BBKNN), the embedding (Harmony, Scanorama) or the expression values (Seurat anchors). A batch effect left at one level propagates to everything downstream.
- Every method can **undercorrect** (batches remain separate) or **overcorrect** (distinct populations merged).
- Mutual nearest neighbours keep only reciprocal cross-batch pairs and are the core of most methods. Harmony instead iterates clustering and within-cluster centroid alignment; slow convergence is a warning sign.
- Results depend on the method and its inputs; check them against biological knowledge.

## Glossary

| Term | Meaning |
| --- | --- |
| Batch | Group of cells sharing technical conditions; often, but not always, one sample |
| Batch effect | Systematic difference between batches unrelated to the question |
| Batch correction (integration) | Removing uninteresting variation between batches |
| Undercorrection / overcorrection | Leaving part of the batch effect / removing interesting variation (e.g., merging cell types) |
| BBKNN | kNN graph in which each cell gets neighbours from every batch |
| Mutual nearest neighbours (MNN) | Cross-batch pair in which each cell is among the other's nearest neighbours |
| Anchor | An MNN pair used to estimate a correction (Seurat) |
| Harmony | Iterative soft clustering plus within-cluster alignment of batch centroids in an embedding |
| CCA | Canonical correlation analysis: directions maximally correlated between two datasets |
| *XIST* | lncRNA expressed in XX cells that silences one X chromosome |

## Further reading

- Polański et al. (2020). BBKNN: fast batch alignment of single cell transcriptomes. *Bioinformatics* 36:964–965.
- Haghverdi et al. (2018). Batch effects in single-cell RNA-sequencing data are corrected by matching mutual nearest neighbors. *Nat. Biotechnol.* 36:421–427.
- Hie, Bryson & Berger (2019). Efficient integration of heterogeneous single-cell transcriptomes using Scanorama. *Nat. Biotechnol.* 37:685–691.
- Korsunsky et al. (2019). Fast, sensitive and accurate integration of single-cell data with Harmony. *Nat. Methods* 16:1289–1296.
- Stuart et al. (2019). Comprehensive integration of single-cell data. *Cell* 177:1888–1902.
- Tran et al. (2020). A benchmark of batch-effect correction methods for single-cell RNA sequencing data. *Genome Biol.* 21:12.
- Luecken et al. (2022). Benchmarking atlas-level data integration in single-cell genomics. *Nat. Methods* 19:41–50.
