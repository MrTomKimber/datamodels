def ww_scorechar(c, loc, target, bchars):
    score=0
    adj=1/(target)
    neg=0
    if c in bchars:
        if loc>target:
            neg=((loc-target)**3)
        score = 1/(((loc-target)**2)+1+neg)
    else:
        score = 1/(((loc-target)**2)+1)*(adj**2)
    return score

def ww(text, target_length):
    linespace=1.0
    breakchars=" ,.-"
    delchars="\n\t"
    for c in delchars:
        text = text.replace(c, " ")
    best_split=0
    texts=[]
    finished=False
    s_text = "".join([t for t in text])
    while not finished and len(s_text)!=0:
        osp=[ww_scorechar(c,e,target_length, breakchars) for e,c in enumerate(s_text)]
        best_split=osp.index(max(osp))
        if len(s_text)==0 or best_split==0 or (target_length * linespace)>len(s_text):
            texts.append(s_text)
            finished=True
        else:
            texts.append(s_text[:best_split+1])
        s_text=s_text[best_split+1:]
    return texts



