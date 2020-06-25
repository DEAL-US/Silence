from silence.settings import settings

###############################################################################
# Utility class for printing a pretty API endpoint tree
###############################################################################
class APITree:
    def __init__(self):
        self.tree = {}
        self.endpoints = []

    def register_endpoint(self, endpoint_data):
        self.endpoints.append(endpoint_data)

    def get_endpoint_list(self):
        return self.endpoints

    def add_url(self, url):
        root = settings.API_PREFIX
        # Strip the API prefix and split by /
        url = url[len(root):]
        if url.startswith("/"):
            url = url[1:]
        spl = url.split("/")
        spl = ["/" + x for x in spl]

        # Update the internal tree info
        if root not in self.tree:
            self.tree[root] = []
        if spl[0] not in self.tree[root]:
            self.tree[root].append(spl[0])

        for token, next_token in zip(spl, spl[1:]):
            if token not in self.tree:
                self.tree[token] = [next_token]
            elif next_token not in self.tree[token]:
                self.tree[token].append(next_token)

    # From https://stackoverflow.com/questions/51903172/how-to-display-a-tree-in-python-similar-to-msdos-tree-command
    def format_tree(self, indent_width=4):
        def _ptree(res, start, parent, tree, grandpa=None, indent=""):
            if parent != start:
                if grandpa is None:  # Ask grandpa kids!
                    res.add(str(parent))
                else:
                    res.add(str(parent) + "\n")
            if parent not in tree:
                return
            for child in tree[parent][:-1]:
                res.add(indent + "├" + "─" * indent_width)
                _ptree(res, start, child, tree, parent, indent + "│" + " " * 4)
            child = tree[parent][-1]
            res.add(indent + "└" + "─" * indent_width)
            _ptree(res, start, child, tree, parent, indent + " " * 5)  # 4 -> 5

        res = _StrCont("")
        start = settings.API_PREFIX
        parent = start
        _ptree(res, start, parent, self.tree)
        return res.get()

    def format_list(self):
        ls = list(map(lambda x: f"{x['route']} ({x['method']})", self.endpoints))
        ls.sort()
        return "\n".join(ls)

class _StrCont:
    def __init__(self, string):
        self.string = string

    def add(self, string):
        self.string += string

    def get(self):
        return self.string