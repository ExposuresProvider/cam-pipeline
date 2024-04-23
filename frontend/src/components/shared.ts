
export function urlToID(url: string) {
    /*
     * Convert a URL into a shorter form that's easier to display and work with.
     */
    const url_lc = url.toLowerCase();
    if (url_lc.startsWith("http://ctdbase.org/detail.go?type=relationship&ixnid=")) return "CTD.RELATIONSHIP:" + url.substring(53);
    if (url_lc.startsWith("http://model.geneontology.org/")) return "GO.MODEL:" + url.substring(30);
    return url;
}
