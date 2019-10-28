from gensim.models import Phrases
from nltk.corpus import stopwords

import matplotlib.pyplot as plt
from collections import Counter
from wordcloud import WordCloud

def get_top_phrases(documents):
    documents_split = [doc.split() for doc in documents]
    remove_from_stop_words = ["would", "what", "which", "who", "whom", "when", "where", "why", "how", "could"]
    words_to_remove = ['yeah', 'okay', 'like', 'oh', 'also', 'and', 'so', 'hey', 'hello']
    custom_stopwords = [sw for sw in stopwords.words('english') if
                        sw not in remove_from_stop_words and sw not in words_to_remove]

    bigram = Phrases(documents_split, min_count=1, delimiter=b' ', common_terms=custom_stopwords)
    trigram = Phrases(bigram[documents_split], min_count=1, delimiter=b' ', common_terms=custom_stopwords)

    cnt = Counter([t for sent in documents_split for t in trigram[bigram[sent]] if t.count(' ') >= 1])
    return cnt.most_common()


def plot_wordcloud(scores):
    s = 0
    for k,v in scores:
        if isinstance(k, tuple) and (k[0]!=k[1]):
            s += v

    token_freqs = {}
    for k,v in scores:
        if isinstance(k, tuple) and (k[0]!=k[1]):
            token_freqs["_".join(k)] = v*1./s
        elif isinstance(k, str):
            token_freqs[k] = v*1./s

    word_cloud = WordCloud(scale=10, background_color="white", prefer_horizontal=0.9,
                       width=800, height=400,
                       min_font_size=8, max_font_size=40)

    word_cloud.generate_from_frequencies(token_freqs)
    fig, ax = plt.subplots(1, 1, figsize=(12,18))
    ax.imshow(word_cloud)
    ax.axis("off")


# plot_wordcloud(get_top_phrases(documents))
