import collections

class SnippetParserStats(object):
    def __init__(self):
        self.snippet_lengths = collections.defaultdict(int)

def merge_stats(stats):
    merged = SnippetParserStats()
    for s in stats:
        for length, count in list(s.snippet_lengths.items()):
            merged.snippet_lengths[length] += count
    return merged

def percentile(distribution, p):
    total = sum(distribution.values())
    threshold = int(p / 100. * total)
    accum = 0
    for value, samples in sorted(distribution.items()):
        if accum + samples >= threshold:
            return value
        accum += samples
    return 0.0
