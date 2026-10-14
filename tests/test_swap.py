"""Swap kit checks on synthetic data (no game cache needed)."""
import os
import sys
import unittest

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, 'tools')]
from osrs.anim import Animator  # noqa: E402
from rsgen import rsformat  # noqa: E402
from rsgen.geom import box  # noqa: E402
from rsgen.swap import fit_rigid, principal_axes, skeleton_plan, swap_worn  # noqa: E402
import swap_verify  # noqa: E402

# a toy skeleton: label 1 and 2 move alike (class), 1 is a rotation centre, 2 never is;
# label 3 and 4 move alike and both are centres
FRAMEMAP = dict(types=[0, 2, 0, 2, 0, 2], maps=[[1], [1, 2], [3], [3, 4], [4], [3, 4]])


def ref_model(labels_by_x):
    m = box(20, 40, 10)
    V = np.rint(m.V * np.array([1, -1, -1])).astype(int)  # RS space
    lab = [labels_by_x(v) for v in V]
    return dict(V=V, F=m.F, vgroup=lab, prio=[10] * len(m.F), priority=10)


class TestSkeletonPlan(unittest.TestCase):
    def test_classes(self):
        plan = skeleton_plan(FRAMEMAP)
        self.assertEqual(plan['cls'][1], plan['cls'][2])
        self.assertEqual(plan['cls'][3], plan['cls'][4])
        self.assertNotEqual(plan['cls'][1], plan['cls'][3])

    def test_cost_counts_how_many_we_add(self):
        from rsgen.swap import _label_cost
        plan = skeleton_plan(FRAMEMAP, counts={3: 5, 4: 2}, body_counts={3: 5, 4: 2})
        self.assertEqual(_label_cost(plan, 2, 100, set()), 0)  # never a centre
        # 100 vertices swamp a centre of 2 more than one of 5
        self.assertGreater(_label_cost(plan, 4, 100, set()), _label_cost(plan, 3, 100, set()))
        self.assertAlmostEqual(_label_cost(plan, 3, 100, set()), 100 / 105)


class TestSwapWorn(unittest.TestCase):
    def test_counts_and_sums_match_original_per_label(self):
        ref = ref_model(lambda v: 1 if v[0] < 0 else 3)
        ours = box(18, 36, 12, ).subdivide().subdivide()  # far more vertices than the original
        plan = skeleton_plan(FRAMEMAP, counts={1: 4, 3: 4}, body_counts={3: 1})
        part = swap_worn(ours, [ref], 'body', plan)[0]
        V = np.asarray(part.V)
        labels = np.array(part.groups)
        # label 1 has a non-centre twin (2): our vertices go there and label 1 keeps
        # exact copies of the original's. Label 3's twin 4 would be an empty centre,
        # so ours stay on 3, with anchors pulling its centroid onto the original's
        self.assertGreater((labels == 2).sum(), 0)
        self.assertGreater((labels == 3).sum(), 0)
        mine3 = np.vstack([V[labels == 3], np.array([p for p, h in part.anchors if h == 3]).reshape(-1, 3)])
        want3 = np.asarray(ref['V'])[np.array(ref['vgroup']) == 3].mean(0)
        self.assertLess(np.abs(mine3.mean(0) - want3).max(), 0.5)
        for g in (1,):
            want_n = sum(1 for x in ref['vgroup'] if x == g)
            want_s = np.asarray(ref['V'])[np.array(ref['vgroup']) == g].sum(0)
            have = [V[labels == g]] + [np.array([p for p, h in part.anchors if h == g]).reshape(-1, 3)]
            have = np.vstack(have)
            self.assertEqual(len(have), want_n, 'label %d count' % g)
            self.assertTrue(np.allclose(have.sum(0), want_s), 'label %d sum' % g)

    def test_encode_keeps_groups_priorities_and_anchors(self):
        ref = ref_model(lambda v: 1 if v[0] < 0 else 3)
        part = swap_worn(box(18, 36, 12).subdivide(), [ref], 'body', skeleton_plan(FRAMEMAP, {1: 4, 3: 4}, {3: 1}))[0]
        sys.path.insert(0, os.path.join(ROOT, 'tools'))
        from swap_build import encode_part
        data, cm, groups, prio = encode_part(part)
        d = rsformat.decode(data)
        self.assertEqual(d['vertex_skins'], groups)
        self.assertEqual(d['priorities'], prio)
        self.assertEqual(sum(1 for a, b, c in d['F'] if a == b == c), len(part.anchors))


class TestFitRigid(unittest.TestCase):
    def test_recovers_orientation(self):
        rod = box(4, 60, 8).move(0, 25, 0)  # a long thing, heavier at one end
        rod.add(box(14, 10, 10).move(0, 50, 0))
        V, F = rod.V, rod.F
        a = np.radians(70)
        R = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
        ref_V = V @ R.T * 1.5 + np.array([30, -100, 5])
        fit = fit_rigid(V, F, ref_V, F)
        self.assertLess(np.abs(fit - ref_V).max(), 1.0)

    def test_principal_axes_sorted(self):
        _, ax, ext = principal_axes(box(4, 60, 10).V, box(4, 60, 10).F)
        self.assertGreater(ext[0], ext[1])
        self.assertGreater(ext[1], ext[2])


class TestAnimatorAndMerge(unittest.TestCase):
    def test_rotation_about_group_centre(self):
        V = np.array([[10, 0, 0], [-10, 0, 0], [0, 0, 10]])
        an = Animator(V, [1, 1, 0])
        fm = dict(types=[0, 2], maps=[[1], [1]])
        P = an.pose(fm, [[0, 0, 0, 0], [1, 0, 128, 0]])  # 128 * 8 = 1024 units: half a turn about y
        self.assertTrue(np.allclose(P[0], [-10, 0, 0], atol=1))
        self.assertTrue(np.allclose(P[1], [10, 0, 0], atol=1))
        self.assertTrue(np.array_equal(P[2], [0, 0, 10]))  # other groups untouched

    def test_client_merge_drops_unused_and_shares_positions(self):
        a = dict(V=np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [9, 9, 9]]), F=[[0, 1, 2]], col=[0] * 1,
                 vgroup=[5, 5, 5, 7])
        b = dict(V=np.array([[0, 0, 0], [0, 0, 1], [1, 0, 0]]), F=[[0, 1, 2]], col=[0], vgroup=[8, 8, 8])
        V, F, C, L, own, P = swap_verify.merged([('a', a), ('b', b)])
        self.assertEqual(len(V), 4)  # unused vertex dropped, two shared
        self.assertEqual(list(L), [5, 5, 5, 8])  # a shared vertex keeps the first label


if __name__ == '__main__':
    unittest.main()
