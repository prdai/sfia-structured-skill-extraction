// Approximates keyword-matcher's nltk pipeline: word_tokenize, lowercase, keep
// alphanumeric tokens, drop English stopwords. Treebank tokenization is not
// reimplemented; splitting on whitespace and stripping edge punctuation agrees
// with it on the records, because any token with interior punctuation
// ("end-to-end", "c++") fails the alphanumeric test under either tokenizer.
const STOPWORDS = new Set([
  "a","about","above","after","again","against","ain","all","am","an","and","any","are","aren",
  "aren't","as","at","be","because","been","before","being","below","between","both","but","by",
  "can","couldn","couldn't","d","did","didn","didn't","do","does","doesn","doesn't","doing","don",
  "don't","down","during","each","few","for","from","further","had","hadn","hadn't","has","hasn",
  "hasn't","have","haven","haven't","having","he","he'd","he'll","he's","her","here","hers",
  "herself","him","himself","his","how","i","i'd","i'll","i'm","i've","if","in","into","is","isn",
  "isn't","it","it'd","it'll","it's","its","itself","just","ll","m","ma","me","mightn","mightn't",
  "more","most","mustn","mustn't","my","myself","needn","needn't","no","nor","not","now","o","of",
  "off","on","once","only","or","other","our","ours","ourselves","out","over","own","re","s",
  "same","shan","shan't","she","she'd","she'll","she's","should","should've","shouldn","shouldn't",
  "so","some","such","t","than","that","that'll","the","their","theirs","them","themselves","then",
  "there","these","they","they'd","they'll","they're","they've","this","those","through","to","too",
  "under","until","up","ve","very","was","wasn","wasn't","we","we'd","we'll","we're","we've","were",
  "weren","weren't","what","when","where","which","while","who","whom","why","will","with","won",
  "won't","wouldn","wouldn't","y","you","you'd","you'll","you're","you've","your","yours",
  "yourself","yourselves",
]);

// Treebank splits clitics off their stem ("organisation's" -> "organisation",
// "'s"), which keeps the stem as an alphanumeric token.
const CLITICS = /['\u2019](s|re|ve|ll|d|m)\b|n['\u2019]t\b/gi;
// Only the punctuation treebank detaches from a word. Hyphens and slashes stay
// attached, so "short-" and "data/information" stay non-alphanumeric and drop.
const DETACHED = String.raw`()\[\]{}"'\u201c\u201d\u2018\u2019.,;:!?\u2026`;
const EDGE_PUNCTUATION = new RegExp(`^[${DETACHED}]+|[${DETACHED}]+$`, "gu");
const ALPHANUMERIC = /^[\p{L}\p{N}]+$/u;

export function tokenize(text: string): string[] {
  return text
    .toLowerCase()
    .replace(CLITICS, " ")
    .split(/\s+/)
    .map((token) => token.replace(EDGE_PUNCTUATION, ""))
    .filter((token) => ALPHANUMERIC.test(token) && !STOPWORDS.has(token));
}
