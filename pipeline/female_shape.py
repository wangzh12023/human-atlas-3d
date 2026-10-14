"""Presentation female: shared build, with local breast and genital differences.

Run from assemble.py, before sex-specific placeholder positions are collapsed.
Never alter vM or re-warp feet, muscle sheets, bones, or other shared anatomy.
"""
import numpy as np
from scipy.interpolate import RBFInterpolator


BREAST_X = 96.0
BREAST_Y = 1258.0
BREAST_RX = 68.0
BREAST_UPPER_RY = 118.0
BREAST_LOWER_RY = 66.0
BREAST_PROJECTION = 56.0


def _footprint(y):
    # Long upper slope, fuller lower pole; gently taper toward the axilla.
    upper = np.clip((np.asarray(y) - BREAST_Y) / BREAST_UPPER_RY, 0, 1)
    upper = upper * upper * (3 - 2 * upper)
    ry = BREAST_LOWER_RY + (BREAST_UPPER_RY - BREAST_LOWER_RY) * (0.5 + 0.5 * np.tanh((np.asarray(y) - BREAST_Y) / 28.0))
    return BREAST_X + 8 * upper, BREAST_RX * (1 - 0.22 * upper), ry


def _chest_terms(x, y):
    x, y = np.asarray(x) / 180.0, (np.asarray(y) - 1280.0) / 130.0
    return np.stack([np.ones_like(x), x * x, y, y * y, x * x * y], axis=-1)


def _breast_radius(x, y):
    center, width, ry = _footprint(y)
    return ((np.abs(x) - center) / width) ** 2 + ((y - BREAST_Y) / ry) ** 2


def _breast_height(x, y):
    return BREAST_PROJECTION * np.maximum(0.0, 1.0 - _breast_radius(x, y)) ** 1.25


def _envelope(surface, side, segments=96, rings=32):
    """Tapered breast volume. Its root is buried in the actual chest wall."""
    vertices = []
    faces = []
    # Front and back disks share one rim. Back lies inside the pectoral surface.
    for back in (False, True):
        start = len(vertices)
        vertices.append([BREAST_X, BREAST_Y, surface(BREAST_X, BREAST_Y) - BREAST_PROJECTION - 12.0
                         if back else surface(BREAST_X, BREAST_Y)])
        for ring in range(1, rings + 1):
            radius = ring / rings
            for angle in np.arange(segments) * (2 * np.pi / segments):
                # Solve the vertical footprint so the radius/contour is also
                # reproducible by the skin sculpt and shader's root blending.
                y = BREAST_Y + radius * np.sin(angle) * (BREAST_UPPER_RY if np.sin(angle) > 0 else BREAST_LOWER_RY)
                for _ in range(16):
                    y = BREAST_Y + radius * np.sin(angle) * _footprint(y)[2]
                center, width, _ = _footprint(y)
                x = center + width * radius * np.cos(angle)
                z = surface(x, y) - _breast_height(x, y) - 12 * (1 - radius ** 2) if back else surface(x, y)
                vertices.append([x, y, z])
        for j in range(segments):
            faces.append([start, start + 1 + j, start + 1 + (j + 1) % segments])
        for ring in range(rings - 1):
            a = start + 1 + ring * segments
            b = a + segments
            for j in range(segments):
                k = (j + 1) % segments
                faces.extend([[a + j, b + j, b + k], [a + j, b + k, a + k]])
        if back:
            first_back_face = segments + (rings - 1) * segments * 2
            faces[first_back_face:] = [f[::-1] for f in faces[first_back_face:]]
    v, f = np.array(vertices), np.array(faces, dtype=np.int64)
    disk_size = 1 + rings * segments
    back_rim = disk_size + 1 + (rings - 1) * segments
    rim_mask = (f >= back_rim) & (f < back_rim + segments)
    f[rim_mask] -= disk_size
    used, remap = np.unique(f, return_inverse=True)
    v, f = v[used], remap.reshape(-1, 3)
    if side < 0:
        v[:, 0] *= -1
        f = f[:, ::-1]
    return v, f


def normalize_female(pieces):
    by_name = {p['en']: p for p in pieces}
    skin = by_name['Skin']
    male_skin = np.asarray(skin['vM'], float)

    # Fit a symmetric, smooth chest wall. Local skin detail must not become
    # folds in the breast envelope or cause fat/skin surface intersections.
    chest = male_skin[(np.abs(male_skin[:, 0]) < 185) &
                      (male_skin[:, 1] > 1150) & (male_skin[:, 1] < 1415) &
                      (male_skin[:, 2] > 150)]
    coefficients = np.linalg.lstsq(_chest_terms(chest[:, 0], chest[:, 1]), chest[:, 2], rcond=None)[0]
    skin_surface = lambda x, y: _chest_terms(x, y) @ coefficients

    # The root follows muscle/rib geometry, rather than floating above it on
    # the skin reference's higher surface. Use smooth bulk but exact contact.
    import open3d as o3d
    scene = o3d.t.geometry.RaycastingScene()
    for p in pieces:
        if p['sex'] or p['system'] not in ('muscles', 'skeleton'):
            continue
        vm = np.asarray(p['vM'], float)
        if vm[:, 1].max() < 1140 or vm[:, 1].min() > 1420 or vm[:, 0].min() > 210 or vm[:, 0].max() < 0:
            continue
        scene.add_triangles(o3d.core.Tensor(vm.astype(np.float32)), o3d.core.Tensor(np.asarray(p['f'], np.uint32)))

    def wall(x, y):
        x, y = np.broadcast_arrays(np.asarray(x, float), np.asarray(y, float))
        rays = np.zeros((x.size, 6), dtype=np.float32)
        rays[:, 0], rays[:, 1], rays[:, 2], rays[:, 5] = np.abs(x).ravel(), y.ravel(), 450, -1
        hits = scene.cast_rays(o3d.core.Tensor(rays))['t_hit'].numpy().reshape(x.shape)
        return np.where(np.isfinite(hits), 450 - hits, skin_surface(x, y) - 14)

    def surface(x, y):
        height = _breast_height(x, y)
        weight = np.clip(height / 14, 0, 1)
        weight = weight * weight * (3 - 2 * weight)
        return (1 - weight) * wall(x, y) + weight * skin_surface(x, y) + height - 2

    # Move female-only pelvic anatomy as one continuous field back into the
    # shared pelvis. Surface + bone correspondences keep internal organs and
    # the vulva patch aligned with their respective supporting structures.
    sources, targets = [], []
    for p in pieces:
        if p['sex'] != 0 or p['system'] not in ('skeleton', 'integument'):
            continue
        vf, vm = np.asarray(p['vF'], float), np.asarray(p['vM'], float)
        mask = (vf[:, 1] > 620) & (vf[:, 1] < 1100) & (np.abs(vf[:, 0]) < 200)
        indices = np.flatnonzero(mask)
        if not len(indices):
            continue
        indices = indices[::max(1, len(indices) // 1800)]
        sources.append(vf[indices]); targets.append(vm[indices])
    src, dst = np.concatenate(sources), np.concatenate(targets)
    src, unique = np.unique(src, axis=0, return_index=True)
    pelvis_displacement = RBFInterpolator(src, dst[unique] - src, neighbors=64,
                                         kernel='linear', smoothing=6.0)

    breast_names = ('Mammary', 'Lactiferous', 'Nipple', 'Areola', 'of Breast', 'Breast Adipose')
    for p in pieces:
        if p['sex'] == 2 and not any(name in p['en'] for name in breast_names):
            v = np.asarray(p['vF'], float)
            p['vF'] = v + pelvis_displacement(v)
        elif p['sex'] == 0:
            p['vF'] = np.asarray(p['vM'], float).copy()

    # Only the female chest surface morphs; feet and the rest of the body use
    # the exact same coordinates as the male, including fine toe attachments.
    v = skin['vF']
    radius = _breast_radius(v[:, 0], v[:, 1])
    mask = (radius < 1) & (v[:, 2] > 150)
    weight = np.clip((1 - radius[mask]) / 0.24, 0, 1)
    weight = weight * weight * (3 - 2 * weight)
    target = skin_surface(v[mask, 0], v[mask, 1]) + _breast_height(v[mask, 0], v[mask, 1]) + 1.8
    # Sculpt outward only. Pulling the original skin inward to a muscle fit
    # creates folds, especially along the underside and axillary boundary.
    v[mask, 2] += weight * np.maximum(0, target - v[mask, 2])
    # Smooth surface normals for the new sculpt, preserving the original
    # normals elsewhere (and keeping male geometry/normals untouched).
    from common import vertex_normals
    normals = vertex_normals(v, skin['f'])
    x, y = v[mask, 0], v[mask, 1]
    smooth_surface = lambda x, y: skin_surface(x, y) + _breast_height(x, y)
    dx = (smooth_surface(x + 0.5, y) - smooth_surface(x - 0.5, y))
    dy = (smooth_surface(x, y + 0.5) - smooth_surface(x, y - 0.5))
    sculpt_normals = np.stack([-dx, -dy, np.ones_like(dx)], axis=1)
    sculpt_normals /= np.linalg.norm(sculpt_normals, axis=1, keepdims=True)
    # BP3D includes locally reversed sheets; retain their orientation so the
    # shader's two-sided lighting does not flip alternate surface triangles.
    sculpt_normals *= np.where(normals[mask, 2:3] >= 0, 1.0, -1.0)
    normals[mask] = normals[mask] * (1 - weight[:, None]) + sculpt_normals * weight[:, None]
    normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)
    skin['normalF'] = normals

    # Preserve HRA ducts/lobes, enlarge them as a coherent assembly, and mirror
    # one reference side so both nipples and breast roots have matching levels.
    old_nipple = np.asarray(by_name['Left Nipple']['vF']).mean(0)
    nipple_x, nipple_y = BREAST_X + 3, BREAST_Y - 2
    nipple_z = surface(nipple_x, nipple_y)
    new_nipple = np.array([nipple_x, nipple_y, nipple_z + 4])
    for p in pieces:
        if p['sex'] != 2 or not any(name in p['en'] for name in breast_names):
            continue
        side = 1 if p['en'].startswith('Left ') else -1
        if 'Breast Adipose' in p['en']:
            p['vF'], p['f'] = _envelope(surface, side)
            p['breast_shape'] = [BREAST_X, BREAST_Y, BREAST_RX, BREAST_UPPER_RY, BREAST_LOWER_RY]
            # Group the complete breast assembly under its existing UI system;
            # otherwise the default anatomy view hides all of its volume.
            p['system'] = 'reproductive'
            p['kind'] = 'proc'
            continue
        reference = by_name['Left ' + p['en'].split(' ', 1)[1]]
        # Keep original reference coordinates until both sides are transformed.
        original = reference.setdefault('_breast_reference', np.asarray(reference['vF'], float).copy())
        scale = [1.08, 0.96, 1.02] if 'Areola' not in p['en'] else [0.95, 0.86, 1.02]
        v = (original - old_nipple) * scale + new_nipple
        if 'Areola' in p['en']:
            v[:, 2] = surface(v[:, 0], v[:, 1]) + 4.2 + (original[:, 2] - np.median(original[:, 2])) * 0.10
        elif 'Nipple' not in p['en']:
            # The soft tissue envelope encloses gland and connective tissue.
            front = surface(v[:, 0], v[:, 1]) - 4
            v[:, 2] = np.minimum(v[:, 2], front)
        f = np.asarray(reference['f']).copy()
        if side < 0:
            v[:, 0] *= -1
            f = f[:, ::-1]
        p['vF'], p['f'] = v, f
    for p in pieces:
        p.pop('_breast_reference', None)

    print('female presentation: shared body/feet, symmetric breasts, aligned pelvic organs')
