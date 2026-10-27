import { BM25_B, BM25_EPSILON, BM25_K1 } from "../src/lib/retrieval-config";
import { tokenize } from "../src/lib/tokenize";

// Port of rank_bm25's BM25Okapi, including its negative-idf floor, so scores
// match keyword-matcher/src/keyword_matcher/matcher.py.
export class BM25 {
  private readonly frequencies: Map<string, number>[];
  private readonly lengths: number[];
  private readonly averageLength: number;
  private readonly idf = new Map<string, number>();

  constructor(documents: string[]) {
    const corpus = documents.map(tokenize);
    this.lengths = corpus.map((tokens) => tokens.length);
    this.averageLength = this.lengths.reduce((sum, length) => sum + length, 0) / corpus.length;
    this.frequencies = corpus.map((tokens) => {
      const counts = new Map<string, number>();
      for (const token of tokens) counts.set(token, (counts.get(token) ?? 0) + 1);
      return counts;
    });

    const documentFrequency = new Map<string, number>();
    for (const counts of this.frequencies) {
      for (const token of counts.keys()) {
        documentFrequency.set(token, (documentFrequency.get(token) ?? 0) + 1);
      }
    }

    const negative: string[] = [];
    let total = 0;
    for (const [token, frequency] of documentFrequency) {
      const idf = Math.log(corpus.length - frequency + 0.5) - Math.log(frequency + 0.5);
      this.idf.set(token, idf);
      total += idf;
      if (idf < 0) negative.push(token);
    }

    const floor = BM25_EPSILON * (total / documentFrequency.size);
    for (const token of negative) this.idf.set(token, floor);
  }

  scores(query: string): number[] {
    const tokens = tokenize(query);
    return this.frequencies.map((counts, index) => {
      const normalization = BM25_K1 * (1 - BM25_B + (BM25_B * this.lengths[index]) / this.averageLength);
      let score = 0;
      for (const token of tokens) {
        const frequency = counts.get(token);
        if (!frequency) continue;
        score += (this.idf.get(token) ?? 0) * ((frequency * (BM25_K1 + 1)) / (frequency + normalization));
      }
      return score;
    });
  }
}
