---
lang: en
title: Lecture 5
permalink: /bf.msu.2026/lecture5/
---
# Lecture 5. Normalization, count distributions and PCA

This lecture is theoretical: it explains *why* the standard preprocessing steps — normalization, log transformation and PCA — are needed, so that they don't feel like a black box. In code they take three lines.

**Starting point.** After QC we have a count matrix: rows are cells, columns are genes, and each entry is a non-negative integer. For 10x data it is a UMI count; for Smart-seq, a read count. We don't yet know which cell types the cells are; finding that out is one of the goals of the next steps.

**How many cells to expect.** One standard 10x channel typically yields roughly 5,000–10,000 cells. Only part of the loaded cells is recovered (on the order of 60%), so to recover \~10,000 cells you load \~16,000. A few percent of the recovered barcodes are doublets. Far more barcodes than expected usually means that empty droplets were not filtered out.

**Why not cluster the raw matrix directly?** You could compute a heatmap with hierarchical clustering straight away. With deep, full-length data (Smart-seq) this sometimes gives something sensible, but with sparse 10x data it gives nonsense, for three reasons:

1. cells are sequenced to different **depths** (Section 2);
2. the **curse of dimensionality** (Section 3);
3. counts are **not normally distributed** (Sections 6–7).

Before going through them, it helps to say what we want instead of the raw matrix.

## 1. Embeddings: what we want

In the strict mathematical sense, an *embedding* is a structure-preserving map. In data-analysis jargon it simply means a **low-dimensional representation** of the data with two properties.

1. **Low dimension.** Each cell is a vector of \~20,000 gene values. An embedding represents it with far fewer coordinates: 2 for visualization (t-SNE, UMAP), or 20–50 for analysis (PCA).
2. **Meaningful distances.** Plain Euclidean distance in the embedding should reflect what we care about: cells of the same type or state should be close, different types far apart. That is what clustering and other methods rely on.

The same idea is used well beyond biology. Text embeddings (from transformer models, used in vector search) map words or documents to vectors so that similar meanings are close. Representing a word by its letter counts is also a vector representation, but useless: similar letters say nothing about similar meaning. Having a vector is not enough; the distances must reflect the similarity we care about.

The rest of the lecture explains why raw counts don't have these properties and what fixes them.

## 2. Problem 1: sequencing depth and normalization

Imagine two genes expressed at exactly the same level in all cells. One cell happened to yield 2 molecules in total, another 4. The cells are identical, yet the Euclidean distance between them is not zero. Across a dataset, differences in **capture and sequencing depth** alone produce a smear of cells — a gradient that reflects technical depth, not biology.

**Fix: normalize by library size.** Divide each cell's counts by its total count (and multiply by a common constant, e.g., 10,000 or the median total). This removes most of the depth effect. In scanpy: `sc.pp.normalize_total(adata)`.

**Which constant.** Common choices are counts per million (CPM, 10⁶), counts per 10,000 (CP10k), and the median total count across cells. Without a log they would differ only by a global scale. Because a log(x + 1) follows, the constant matters slightly: the larger it is, the larger normalized values are relative to the pseudocount 1, which changes how strongly small values are compressed. Strong effects don't depend on this choice, but borderline ones can. Scaling to the median keeps a typical cell's values on its original count scale, which is a sensible default.

**After division, values are no longer counts.** Normalized values are not integers, so strictly they no longer follow a negative binomial. Treating them as approximately NB is fine in practice, especially with median scaling, where most cells are rescaled only moderately.

**Diagnosing a leftover depth effect.** Once you have a 2D visualization (UMAP, Lecture 6), color it by total counts per cell. If low-count cells form streaks or bridges between clusters, or are pulled toward the centre of the plot, depth is still driving part of the structure.

## 3. Problem 2: the curse of dimensionality, and rank

**The curse of dimensionality.** As the number of dimensions grows, distances between points become more and more alike. A simple experiment shows this: scatter 10 points uniformly at random in \[0, 1\]^d and compare the largest pairwise distance with the smallest.

- In 1 dimension the ratio can be over 100.
- In 2 dimensions it may be \~25, and in 3 dimensions \~3.
- From about 10 dimensions on it stays between 1 and 2, i.e. all points are roughly equally far from each other.

When all distances look alike, nearest neighbours, clusters and classifiers stop being meaningful. This holds for all common distances (Euclidean, L1, correlation…), although some, such as correlation distance, are somewhat more robust.

**Rank: the dimensions that actually matter.** What counts is not how many coordinates the data have, but the **rank** of the space they occupy — the number of independent directions (degrees of freedom).

- Points lying on a flat sheet embedded in 3D have three coordinates but rank 2.
- If gene 1 always equals 2 × gene 2, two measured genes give a space of rank 1.

Genes are strongly correlated (co-regulated modules), so cell states live in a space of much lower rank than 20,000 — typically tens of dimensions. Noise hides this: scatter around the true low-rank structure makes the measured data formally full-rank. The task, then, is to find the low-rank subspace and treat the rest as noise.

## 4. SVD and PCA

PCA and SVD (singular value decomposition) are two formulations of the same procedure, applied to centred data. Textbooks introduce them in different ways (via SVD, via the covariance matrix, via maximum variance), which is confusing at first. All of them describe the same thing, and it is worth working through why.

**A matrix as a transformation.** We usually think of the data matrix as a stack of cell vectors. In linear algebra, though, a matrix is a linear transformation. Any matrix *M* can be written as

```latex
M = U \Sigma V^{T}
```

This reads as a rotation (*V*ᵀ), a stretching along the axes (Σ), and another rotation (*U*).

- *U* and *V* are orthonormal: their columns are perpendicular unit vectors.
- Σ is diagonal. Its entries, the **singular values**, say how strongly each direction is stretched.
- The "rotated axes" are linear combinations of genes.

**Truncation: the best low-rank approximation.** Keep only the k largest singular values and set the rest to zero. The product then has rank k, and it is the **best rank-k approximation** of the data (the Eckart–Young theorem). No other rank-k subspace gives a smaller sum of *squared* distances from the original points to their projections.

**Two equivalent views of PCA.**

- The subspace that minimizes squared projection distances (reconstruction error).
- The subspace that maximizes the variance of the projected points (for k components, the total variance, i.e. the trace of the covariance).

Both give the same answer.

**What PCA returns: two matrices.**

- **Scores** (cells × k): the coordinates of each cell in the low-rank space. Stored in `adata.obsm["X_pca"]`.
- **Loadings** (genes × k): how each gene contributes to each component. Stored in `adata.varm["PCs"]`.

Their product reconstructs a (centred) approximation of the original matrix, which looks 20,000-dimensional but has rank k.

A helpful picture for biologists is to think of components as **gene modules**. A cell's scores tell how active each module is in it; a gene's loadings tell how much it contributes to each module. A gene's reconstructed expression in a cell is the sum over modules of (module activity × gene's weight in that module). Bear in mind that PCA components are mathematical directions, not necessarily biological programmes.

**Matrix factorization in general.** PCA is one member of a large family: approximate a matrix as the product of two smaller ones. Different constraints on the factors give different methods. NMF requires non-negative factors; topic models such as LDA require the factors to be proportions.

## 5. Centering and scaling

Before PCA the data are usually **z-scored** gene by gene: subtract each gene's mean, then divide by its **standard deviation**. Each gene then has mean 0 and variance 1.

- **Centering** is essential. PCA describes variation around the mean; without centering, the first component mostly captures the mean itself.
- **Scaling to unit variance** keeps a few genes with very large variance from dominating the components. Gene variances differ for many reasons that are not interesting, mostly their expression level. In scanpy, `sc.pp.scale(adata, max_value=10)` also clips extreme values.

Homework for the curious: think about what multiplying a new cell's (centred) expression vector by the covariance matrix (genes × genes) gives you. Once that is clear, the need for centering and scaling becomes obvious.

## 6. Problem 3: counts are not normally distributed

**What PCA implicitly assumes.** Minimizing squared error is the right thing to do when the data lie near a low-rank subspace plus **symmetric, roughly Gaussian noise** around it. Formally, PCA is the maximum-likelihood solution under isotropic Gaussian noise (probabilistic PCA). Count data violate this: counts are non-negative integers, and their noise is not symmetric.

**The "time machine" thought experiment.** Imagine sequencing the *same* cell many times. The counts would differ from run to run, simply because each run captures a random subset of the molecules. That **sampling noise** sets the minimum noise in the data.

**The hat model.** Think of a cell as a hat full of coloured balls (molecules of different genes). You randomly draw a fixed number of balls and count the red ones, then repeat.

- With few red balls in the hat, you usually draw 0 or 1, sometimes 2 or 3.
- With more red balls, the distribution shifts right and becomes wider.
- Scaling the hat and the number of red balls by the same factor changes nothing. Only the *fraction* of red balls matters, so this is a one-parameter model.

Strictly, drawing from a hat is binomial (or hypergeometric) sampling. When each gene is a small fraction of all molecules, it is well approximated by the **Poisson distribution**.

**The key property: variance equals mean.** Highly expressed genes have larger variance purely from sampling, so on raw counts they would dominate PCA. A plot of variance against mean across genes would lie on the diagonal.

**Variance-stabilizing transformation.** For Poisson data, the **square root** (more precisely, the Anscombe transform 2√(x + 3/8)) makes the variance approximately constant and the distribution closer to symmetric, which PCA can handle.

## 7. Overdispersion and the negative binomial

In real data, even in a homogeneous cell line sorted to a single state, the variance grows **faster than the mean**. A gene with a mean of 100 counts can have a variance of thousands. This excess over Poisson is called **overdispersion**. Note the definition: Poisson variance equal to the mean is *not* overdispersion, however large it is. Overdispersion means variance greater than the mean.

**Where it comes from.** In the hat model, the hat itself is not identical from draw to draw. Cells of the same type differ stochastically (transcriptional bursting). Library preparation also adds variation: in one run slightly more molecules are lost than in another. So the Poisson rate λ is not fixed but varies.

**The model.** If λ follows a **gamma distribution** (a natural choice for a positive quantity), the resulting counts follow a **negative binomial (NB)** distribution, also called the gamma–Poisson distribution. Its variance is

```latex
\mathrm{Var} = \mu + \frac{\mu^2}{\theta}
```

- μ is the mean and θ is the dispersion parameter (smaller θ, more overdispersion).
- The quadratic term is why overdispersion is barely visible for lowly expressed genes and becomes obvious for highly expressed ones.
- The NB is the default model for count data in genomics, much as the normal distribution is for continuous data.

If you remember two technical ideas from the first half of the course, make it how Illumina sequencing works and the negative binomial as a gamma–Poisson mixture.

**The practical fix: log transform.** For NB data no single simple transformation is perfect. However, `log(x + 1)` applied to depth-normalized counts is approximately variance-stabilizing for the higher counts that dominate PCA, and makes the distribution far more symmetric. The pseudocount 1 keeps zeros at zero. In scanpy: `sc.pp.log1p(adata)`. This is one reason log scales are used so widely for count data in omics.

**The shifted logarithm.** Written out, the transform is log(y / s + y₀), where *y* is the raw count, *s* the cell's size factor and y₀ the pseudocount. y₀ = 1 is a convention. The variance-stabilizing transform derived for the NB corresponds to a pseudocount that depends on the overdispersion and is usually fractional; with y₀ = 1, zeros map exactly to zero and the matrix stays sparse.

**Where the log works poorly.** The approximation holds for genes with large counts. For low-mean genes, the log-normalized distribution is a spike at zero plus separate bumps from cells that had 1, 2, 3 counts (smeared by different size factors). It is far from normal, and this is an artifact of transforming small integers, not biology.

**A side effect of the log.** It compresses the huge variances of highly expressed genes, so a handful of genes no longer dominates distances. As a result, even distances in the full log-normalized gene space become reasonably meaningful, although PCA remains the better space to work in.

## 8. A side story: underdispersion as a red flag

Because sampling alone produces Poisson-level variation, counts with *less* variance than Poisson (**underdispersion**) are suspicious.

Dmitry Kobak applied this to reported daily Covid-19 numbers. In autumn 2021 Russia reported almost exactly \~800 deaths per day. A Poisson process with that mean would have a variance of about 800, but the observed variance over a week was about 9. Screening the WHO data, he found statistically significant underdispersion in about 20 countries. Most of them are known from excess-mortality data to strongly undercount Covid deaths.

The general principle is the same one used in statistical forensics of reported numbers and elections. Establish what distribution is expected and how most comparable cases behave. Deviations from it do not prove manipulation — there can be legitimate explanations — but they need to be explained.

## 9. Dropouts and zero inflation

The word **"dropout"** is often used loosely for any zero where a gene "should" be expressed, e.g., a CD4 T cell with zero *CD4* counts. But expression is a distribution: a gene with a low mean will often produce a zero by chance. That zero is an expected sample, not a missing value.

In the strict statistical sense, **zero inflation** means more zeros than the count model (e.g., the NB) predicts. It is a property of the data-generating process, not of an individual zero; you can't say which specific zero is a "dropout". Early single-cell papers modelled it with a third, zero-inflation parameter (zero-inflated NB).

For droplet data with UMIs, it turned out that the NB already explains the zeros well: droplet scRNA-seq is not zero-inflated (Svensson, 2020). Apparent excess zeros often come from mixing populations. Two cell types with different means, pooled together, look like one distribution with "too many" zeros.

## 10. Beyond log + PCA

Several more principled approaches exist.

- **Model-based normalization.** These methods model depth explicitly instead of simply dividing by it, since division makes counts non-integer and breaks the count model. **sctransform** fits a regularized NB regression per gene with sequencing depth as a covariate and uses the Pearson residuals. **Analytic Pearson residuals** are a simpler closed-form version.
- **GLM-PCA.** This generalizes PCA to non-Gaussian data. The low-rank (linear) part models the parameters of the count distribution, e.g. the log of the Poisson or NB mean. A non-linear link (exponentiation) connects it to the expected counts, and the fit maximizes the count likelihood instead of minimizing squared error.
- **Other matrix factorizations** with different constraints, such as non-negative matrix factorization (NMF).

**What works best in practice.** A 2023 benchmark of transformations for single-cell data (Ahlmann-Eltze & Huber) found that the simple **shifted logarithm followed by PCA** performs as well as or better than the more sophisticated alternatives. That is what we will use in this course.

## 11. Summary: the standard recipe

We want to cluster the count matrix, but cannot do it directly for three reasons, and each has a standard fix.

| Problem | Fix | scanpy |
| --- | --- | --- |
| Different sequencing depth per cell | Normalize to library size | `sc.pp.normalize_total(adata)` |
| Counts are not normal (overdispersed NB) | Log transform | `sc.pp.log1p(adata)` |
| Curse of dimensionality | Project onto a low-rank subspace with PCA (after scaling) | `sc.pp.scale(adata, max_value=10)`; `sc.pp.pca(adata)` |

The code is trivial; the point of this lecture is to understand why each line is there. Next time we build 2D embeddings (t-SNE, UMAP) on top of PCA in practice.

## 12. Key points and glossary

1. Raw counts can't be clustered directly because of depth differences, non-normal count noise, and high dimensionality.
2. Normalizing to library size removes most depth effects.
3. In high dimensions, distances become alike. Cell states, however, live in a low-rank space because genes are correlated.
4. SVD/PCA gives the best low-rank approximation (minimum squared error = maximum variance), returning cell scores and gene loadings.
5. PCA implicitly assumes symmetric, Gaussian-like noise, so count data must be transformed first. Center (and usually scale) genes before PCA.
6. Sampling noise is Poisson (variance = mean). Real data are overdispersed (variance > mean) and follow a negative binomial (gamma–Poisson).
7. Square root stabilizes Poisson variance; log(x+1) is the practical choice for NB-like data.
8. Not every zero is a "dropout": UMI data are well described by the NB without zero inflation.
9. Despite fancier methods (sctransform, Pearson residuals, GLM-PCA), log-normalization + PCA performs as well as anything in benchmarks.

| Term | Meaning |
| --- | --- |
| Embedding | Low-dimensional representation where distances are meaningful |
| Library size / depth | Total counts per cell |
| Curse of dimensionality | Concentration of distances in high-dimensional spaces |
| Rank | Number of independent directions in which the data vary |
| SVD | M = UΣVᵀ: rotation, scaling, rotation |
| Singular values | Diagonal of Σ; how much each direction stretches |
| PCA scores / loadings | Cell coordinates on components / gene weights of components |
| Z-scoring | Subtract mean, divide by standard deviation |
| Poisson distribution | Count distribution with variance equal to the mean |
| Overdispersion | Variance greater than the mean |
| Negative binomial | Gamma–Poisson mixture; Var = μ + μ²/θ |
| Variance-stabilizing transformation | Transformation making variance roughly independent of the mean (√ for Poisson, log for NB-like data) |
| Zero inflation | More zeros than the count model predicts |
| GLM-PCA | PCA generalized to count likelihoods via a link function |

## Further reading

- [Kobak — Underdispersion: a statistical anomaly in reported Covid data](https://dkobak.github.io/pdfs/kobak2022underdispersion.pdf)
- [Svensson, 2020 — Droplet scRNA-seq is not zero-inflated](https://doi.org/10.1038/s41587-019-0379-5)
- [Ahlmann-Eltze & Huber, 2023 — Comparison of transformations for single-cell RNA-seq data](https://doi.org/10.1038/s41592-023-01814-1)
- [Townes et al., 2019 — Feature selection and dimension reduction for scRNA-seq based on a multinomial model (GLM-PCA)](https://doi.org/10.1186/s13059-019-1861-6)
- [Hafemeister & Satija, 2019 — sctransform](https://doi.org/10.1186/s13059-019-1874-1)
