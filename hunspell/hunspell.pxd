cdef extern from "hunspell/hunspell.hxx":
    cdef cppclass Hunspell:
        Hunspell(const char *affpath, const char *dpath, const char *key = NULL) nogil

        # load extra dictionaries (only dic files)
        int add_dic(const char * dpath, const char * key = NULL) nogil

        # spell(word) - spellcheck word
        # output: 0 = bad word, not 0 = good word
        #
        # plus output:
        #   info: information bit array, fields:
        #     SPELL_COMPOUND  = a compound word
        #     SPELL_FORBIDDEN = an explicit forbidden word
        #   root: root (stem), when input is a word with affix(es)

        bint spell(const char * word, int * info = NULL, char ** root = NULL) nogil

        # suggest(suggestions, word) - search suggestions
        # input: pointer to an array of strings pointer and the (bad) word
        #   array of strings pointer (here *slst) may not be initialized
        # output: number of suggestions in string array, and suggestions in
        #   a newly allocated array of strings (*slts will be NULL when number
        #   of suggestion equals 0.)

        int suggest(char*** slst, const char * word) nogil

        # deallocate suggestion lists

        void free_list(char *** slst, int n) nogil

        char * get_dic_encoding() nogil

        # morphological functions

        # analyze(result, word) - morphological analysis of the word

        int analyze(char*** slst, const char * word) nogil

        # stem(result, word) - stemmer function

        int stem(char*** slst, const char * word) nogil

        # stem(result, analysis, n) - get stems from a morph. analysis
        # example:
        # char ** result, result2;
        # int n1 = analyze(&result, "words");
        # int n2 = stem(&result2, result, n1);

        int stem(char*** slst, char ** morph, int n) nogil

        # generate(result, word, word2) - morphological generation by example(s)

        int generate(char*** slst, const char * word, const char * word2) nogil

        # generate(result, word, desc, n) - generation by morph. description(s)
        # example:
        # char ** result;
        # char * affix = "is:plural"; // description depends from dictionaries, too
        # int n = generate(&result, "word", &affix, 1);
        # for (int i = 0; i < n; i++) printf("%s\n", result[i]);

        int generate(char*** slst, const char * word, char ** desc, int n) nogil

        #
        # functions for run-time modification of the dictionary
        #

        # add word to the run-time dictionary

        int add(const char * word) nogil

        # add word to the run-time dictionary with affix flags of
        # the example (a dictionary word): Hunspell will recognize
        # affixed forms of the new word, too.

        int add_with_affix(const char * word, const char * example) nogil

        # remove word from the run-time dictionary

        int remove(const char * word) nogil
