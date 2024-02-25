class t:
    def it(self):
        i = 0
        while i < 20:
            i += 1
            yield i


a = t()
b = a.it()

for j in b:
    print(j)
