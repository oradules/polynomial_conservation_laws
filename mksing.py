
import os, sys, glob, re, json
import sympy
from sympy import sympify as S


db_path = r"i:\git\odebase\data\db"

var_pat = re.compile(r"([xk])([0-9]+)")


def singstr(f):
    """
    >>> singstr(S("a+b"))
    '(a + b)'
    >>> singstr(S("a*b"))
    '(a*b)'
    >>> singstr(S("a**b"))
    '(a^b)'
    >>> singstr(S("a+b*c**2"))
    '(a + (b*(c^2)))'
    >>> singstr(S("a+b*c**4/2"))
    '(a + (1/2*b*(c^4)))'
    >>> singstr(S("a*(b+c)"))
    '(a*(b + c))'
    >>> singstr(S("a**(b+c)"))
    '(a^(b + c))'
    """
    if f.func == sympy.Add:
        return "(" + " + ".join([singstr(i) for i in f.args]) + ")"
    if f.func == sympy.Mul:
        return "(" + "*".join([singstr(i) for i in f.args]) + ")"
    if f.func == sympy.Pow:
        assert len(f.args) == 2
        return f"({singstr(f.args[0])}^{singstr(f.args[1])})"
    
    assert len(f.args) == 0
    return str(f)


def tosing(s):
    return var_pat.sub(lambda m: f"{m.group(1)}({m.group(2)})", str(s))


class HasDenominator(Exception):
    pass

class NoOutput(Exception):
    pass


def mkit(str_sys, nb):
    p = []
    syms = set()
    has_zero = False

    for str_eq in str_sys:
        f = sympy.sympify(str_eq)
        fl = f.lhs
        fr = f.rhs
        syms |= f.free_symbols

        fr = fr.expand()

        # filter out all polynomials where anything (even constants) is in the denominator
        for _,(_,exp,_) in fr.as_terms()[0]:
            if any(i < 0 for i in exp):
                #print(fr)
                raise HasDenominator

        s = tosing(singstr(fr))
        assert S(s) == S(tosing(fr)), f"s = {s}, fr = {fr}"
        p.append(s)
        has_zero |= s == "0"

    # filter only symbols starting with 'k' and sort them properly
    kk = [str(i) for i in syms]
    vv = sorted([int(i[1:]) for i in kk if i.startswith('x')])
    kk = sorted([int(i[1:]) for i in kk if i.startswith('k')])
    kk = [tosing(f'k{i}') for i in kk]
    kk = ','.join(kk)
    vv = [tosing(f'x{i}') for i in vv]
    vv = ','.join(vv)
    pp = ',\n'.join(p)

    return f"""
proc bm{nb}() {{
    ring r = (0, {kk}), ({vv}), dp;
    ideal i =
{pp};
    polconslaw(r, i);
}};
""", f"bm{nb}();" + "\n", has_zero


def do_one(fn):
    r"""
    # >>> x = do_one(os.path.join(db_path, "BIOMD0000000292", "data.json"))
    # >>> print(end=x[0])
    # <BLANKLINE>
    # proc bm292() {
    #     ring r = (0, k(1),k(2),k(3),k(4),k(7)), (x(1),x(2),x(3),x(4),x(5),x(6)), dp;
    #     ideal i =
    # -k(2)*x(3) + k(4)*x(6),
    # -k(1)*x(4) - k(2)*x(3) + 2*k(3)*x(2)*x(6),
    # -k(1)*x(4) + k(2)*x(3),
    # 0;
    #     polconslaw(r, i);
    # };
    # >>> print(end=x[1])
    # bm292();
    # >>> x[2]
    # True

    # >>> do_one(os.path.join(db_path, "BIOMD0000000556", "data.json"))
    # Traceback (most recent call last):
    #   ...
    # NoOutput
    """
    nb = int(os.path.basename(os.path.dirname(fn))[5:])

    with open(fn) as f:
        s = f.read()
        d = json.loads(s)
        if not (d["error_count"] == 0 and
            d["warn_count"] == 0 and
            d["computed_poly_rat"] and
            d["is_strictly_polynomial"] and
            not d["has_time"] and
            not d["has_delay"] and
            not d["has_piecewise"] and
            not d["has_unmapped_symbols"] and
            not d["has_double_definition"] and
            d["num_events"] == 0 and
            d["num_constraints"] == 0 and
            d["num_species_types"] == 0 and
            d["num_compartment_types"] == 0 and
            not d["has_both_quantity_types"] and
            not d["has_reactive_species_with_rule"] and
            d["num_species"] > 0 and
            not d["species_const_not_boundary_condition"] and
            not d["has_parameter_rate_rule"] and
            True):
            raise NoOutput

        try:
            return mkit(d["all_odes_sympy"], nb)
        except HasDenominator:
            raise NoOutput


def main():
    r_has_zero = ""
    r_non_zero = ""
    l = []
    for fn in glob.glob(os.path.join(db_path, "**", "data.json"), recursive=True):
        print(end=f"\r{fn}", file=sys.stderr)

        try:
            func_text, func_call, has_zero = do_one(fn)
        except NoOutput:
            continue

        if has_zero:
            r_has_zero += func_text
        else:
            r_non_zero += func_text
        l.append(func_call)
        print(file=sys.stderr)

    print(file=sys.stderr)

    s = f"""
LIB "polconslaw.lib";

{r_non_zero}

{r_has_zero}

proc allbm_non_zero() {{
    {'    '.join(l)}}};

proc allbm_has_zero() {{
    {'    '.join(l)}}};
"""

    with open("allbm_new2.lib", "w", newline="\n") as f:
        f.write(s)

    s = s.replace(" bm", " genbm").replace("polconslaw", "genpolconslaw").replace("allbm", "genallbm")
    with open("allbm-gen_new2.lib", "w", newline="\n") as f:
        f.write(s)


if __name__ == "__main__":
    import doctest
    doctest.testmod()

    main()
