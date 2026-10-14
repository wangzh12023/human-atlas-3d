// Region close-up definitions: which structures belong to a region, how the camera frames it,
// and which systems are shown. Pairs with content/regions.js (texts) by id.
//
// match: regexes tested against the English piece name (case-insensitive).
// view : yaw (0 = front, PI = back, +PI/2 = subject's left side), pitch, fill (screen fraction)
// show : systems kept visible while the close-up is active (others are hidden)
// side : 'L' | 'R' | 'both' -> which body side to frame (structures on both sides are still highlighted)
// context: regexes for structures kept visible but not highlighted (dimmed)

const PI = Math.PI;
const SK = ['skeleton', 'ligaments'];

export const REGION_DEFS = {
  shoulder: {
    ghost: [/^skin$/i],
    match: [/deltoid$/i, /supraspinatus/i, /infraspinatus/i, /teres minor/i, /subscapularis/i, /teres major/i],
    context: [/humerus/i, /scapula/i, /clavicle/i, /biceps brachii/i, /triceps brachii/i, /pectoralis/i, /trapezius/i],
    show: ['skeleton', 'muscles', 'ligaments'], side: 'R', view: { yaw: -0.9, pitch: 0.18, fill: 0.62 }, hotspot: /acromial part of right deltoid/i,
  },
  chest: {
    ghost: [/^skin$/i],
    match: [/pectoralis major/i, /pectoralis minor/i, /serratus anterior/i, /intercostal/i, /^(left|right) (first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|eleventh|twelfth) rib/i, /body of sternum|manubrium|xiphoid/i, /costal cartilage/i, /subclavius/i],
    show: ['skeleton', 'muscles', 'ligaments'], side: 'both', view: { yaw: 0.25, pitch: 0.12, fill: 0.6 }, hotspot: /sternocostal part of left pectoralis major/i,
  },
  upper_back: {
    ghost: [/^skin$/i],
    match: [/trapezius/i, /rhomboid/i, /levator scapulae/i, /serratus posterior superior/i, /spinal part of .* deltoid/i],
    context: [/scapula/i, /thoracic vertebra/i, /rib$/i],
    show: ['skeleton', 'muscles', 'ligaments'], side: 'both', view: { yaw: PI - 0.2, pitch: 0.2, fill: 0.62 }, hotspot: /transverse part of left trapezius/i,
  },
  arm: {
    ghost: [/^skin$/i],
    match: [/biceps brachii/i, /brachialis$/i, /triceps brachii/i, /coracobrachialis/i, /humerus/i],
    context: [/deltoid/i, /radius/i, /ulna$/i],
    show: ['skeleton', 'muscles', 'ligaments', 'arteries', 'veins'], side: 'R', view: { yaw: -0.55, pitch: 0.08, fill: 0.62 }, hotspot: /long head of right biceps brachii/i,
  },
  elbow_forearm: {
    ghost: [/^skin$/i],
    match: [/brachioradialis/i, /flexor carpi/i, /extensor carpi/i, /pronator/i, /supinator/i, /palmaris longus/i, /flexor digitorum (superficialis|profundus)/i, /extensor digitorum$/i, /anconeus/i, /radius$/i, /ulna$/i, /interosseous membrane of .* forearm/i, /abductor pollicis longus/i, /extensor pollicis/i, /flexor pollicis longus/i, /extensor indicis/i, /extensor digiti minimi/i],
    show: ['skeleton', 'muscles', 'ligaments'], side: 'R', view: { yaw: -0.4, pitch: 0.1, fill: 0.6 }, hotspot: /right brachioradialis/i,
  },
  wrist_hand: {
    ghost: [/^skin$/i],
    match: [/phalanx of .* (finger|thumb)/i, /metacarpal/i, /scaphoid|lunate|triquetral|pisiform|trapezium|trapezoid|capitate|hamate/i, /flexor retinaculum/i, /(pollicis brevis|opponens pollicis|adductor pollicis|of .* hand|lumbricals of|interossei of)/i],
    show: ['skeleton', 'muscles', 'ligaments', 'arteries'], side: 'R', view: { yaw: -0.3, pitch: 0.25, fill: 0.62 }, hotspot: /right capitate/i,
  },
  neck: {
    ghost: [/^skin$/i],
    match: [/sternocleidomastoid/i, /scalenus/i, /splenius/i, /levator scapulae/i, /cervical vertebra|^atlas$|^axis$/i, /intervertebral disk of (axis|.* cervical)/i, /longus (colli|capitis)/i, /semispinalis (capitis|cervicis)/i, /hyoid|omohyoid|sternohyoid|sternothyroid|thyrohyoid/i, /descending part of .* trapezius/i],
    context: [/common carotid|internal jugular|vertebral artery/i, /trachea|thyroid cartilage/i],
    show: ['skeleton', 'muscles', 'ligaments', 'arteries', 'veins', 'respiratory'], side: 'both', view: { yaw: 0.6, pitch: 0.1, fill: 0.58 }, hotspot: /right sternocleidomastoid/i,
  },
  core: {
    ghost: [/^skin$/i],
    match: [/external oblique/i, /linea alba/i, /rectus abdominis/i, /internal oblique/i, /transversus abdominis/i, /diaphragm/i, /abdominal part of .* pectoralis/i, /serratus anterior/i],
    context: [/rib$/i, /costal cartilage/i, /hip bone/i],
    show: ['skeleton', 'muscles', 'ligaments'], side: 'both', view: { yaw: 0.15, pitch: 0.05, fill: 0.62 }, hotspot: /linea alba/i,
  },
  lower_back: {
    ghost: [/^skin$/i],
    match: [/iliocostalis/i, /longissimus/i, /spinalis/i, /lumbar vertebra/i, /intervertebral disk of .* lumbar/i, /quadratus lumborum/i, /psoas major/i, /multifidus/i, /lumbar rotator|interspinales lumborum|lumbar intertransversarius/i, /serratus posterior inferior/i, /latissimus/i],
    context: [/sacrum/i, /hip bone/i, /twelfth rib/i],
    show: ['skeleton', 'muscles', 'ligaments', 'nervous'], side: 'both', view: { yaw: PI + 0.35, pitch: 0.12, fill: 0.62 }, hotspot: /right iliocostalis lumborum/i,
  },
  spine: {
    match: [/vertebra$/i, /^atlas$|^axis$/i, /sacrum/i, /coccyx/i, /intervertebral disk/i, /spinal cord|central canal of spinal cord/i],
    show: ['skeleton', 'ligaments', 'nervous'], side: 'both', view: { yaw: PI / 2 + 0.15, pitch: 0.05, fill: 0.86 }, hotspot: /twelfth thoracic vertebra/i,
  },
  hip: {
    ghost: [/^skin$/i],
    match: [/hip bone/i, /femur/i, /iliacus/i, /psoas major/i, /pectineus/i, /tensor fasciae latae/i, /gluteus minimus/i, /obturator/i, /quadratus femoris/i, /gemellus/i, /piriformis/i],
    context: [/sacrum/i, /coccyx/i],
    show: ['skeleton', 'muscles', 'ligaments'], side: 'R', view: { yaw: -0.6, pitch: 0.12, fill: 0.6 }, hotspot: /right iliacus/i,
  },
  glutes: {
    ghost: [/^skin$/i],
    match: [/gluteus (maximus|medius|minimus)/i, /piriformis/i, /gemellus/i, /obturator internus/i, /quadratus femoris/i],
    context: [/hip bone/i, /sacrum/i, /femur/i, /iliotibial/i],
    show: ['skeleton', 'muscles', 'ligaments'], side: 'both', view: { yaw: PI + 0.5, pitch: 0.12, fill: 0.62 }, hotspot: /right gluteus maximus/i,
  },
  pelvic_floor: {
    ghost: [/^skin$/i],
    match: [/iliococcygeus|pubococcygeus|puborectalis/i, /coccygeus/i, /external anal sphincter/i, /tendinous arch of levator ani/i, /perineal muscle/i],
    context: [/hip bone/i, /sacrum/i, /coccyx/i, /urinary bladder/i, /rectum/i, /prostate/i, /uter|vagin/i],
    show: ['skeleton', 'muscles', 'ligaments', 'urinary', 'digestive', 'reproductive'], side: 'both', view: { yaw: 0.2, pitch: -0.75, fill: 0.62 }, hotspot: /right pubococcygeus/i,
  },
  quads: {
    ghost: [/^skin$/i],
    match: [/rectus femoris/i, /vastus/i, /sartorius/i, /quadriceps tendon/i],
    context: [/femur/i, /patella$/i, /tensor fasciae latae/i],
    show: ['skeleton', 'muscles', 'ligaments'], side: 'R', view: { yaw: -0.35, pitch: 0.05, fill: 0.7 }, hotspot: /right rectus femoris/i,
  },
  hamstrings: {
    ghost: [/^skin$/i],
    match: [/biceps femoris/i, /semitendinosus/i, /semimembranosus/i],
    context: [/femur/i, /hip bone/i, /gluteus maximus/i, /gastrocnemius/i],
    show: ['skeleton', 'muscles', 'ligaments'], side: 'R', view: { yaw: PI + 0.3, pitch: 0.05, fill: 0.7 }, hotspot: /long head of right biceps femoris/i,
  },
  adductors: {
    ghost: [/^skin$/i],
    match: [/adductor (longus|brevis|magnus|minimus)/i, /gracilis/i, /pectineus/i],
    context: [/femur/i, /hip bone/i],
    show: ['skeleton', 'muscles', 'ligaments'], side: 'R', view: { yaw: 0.55, pitch: 0.08, fill: 0.7 }, hotspot: /right adductor longus/i,
  },
  itb: {
    ghost: [/^skin$/i],
    match: [/iliotibial tract/i, /tensor fasciae latae/i, /gluteus maximus/i, /vastus lateralis/i],
    context: [/femur/i, /tibia$/i, /fibula$/i, /hip bone/i],
    show: ['skeleton', 'muscles', 'ligaments'], side: 'R', view: { yaw: -PI / 2 - 0.05, pitch: 0.05, fill: 0.8 }, hotspot: /right iliotibial tract/i,
  },
  knee: {
    ghost: [/^skin$/i],
    match: [/cruciate/i, /meniscus/i, /collateral ligament of .*knee/i, /patellar ligament/i, /quadriceps tendon/i, /patella$/i, /popliteus/i],
    context: [/femur/i, /tibia$/i, /fibula$/i],
    show: ['skeleton', 'ligaments'], side: 'R', view: { yaw: -0.5, pitch: 0.1, fill: 0.6 }, hotspot: /right patella$/i, box: 'knee',
  },
  calf: {
    ghost: [/^skin$/i],
    match: [/gastrocnemius/i, /soleus/i, /plantaris/i, /tibialis posterior/i, /popliteus/i, /flexor digitorum longus/i, /flexor hallucis longus/i, /calcaneal tendon/i],
    context: [/tibia$/i, /fibula$/i],
    show: ['skeleton', 'muscles', 'ligaments'], side: 'R', view: { yaw: PI + 0.35, pitch: 0.05, fill: 0.72 }, hotspot: /medial head of right gastrocnemius/i,
  },
  shin: {
    ghost: [/^skin$/i],
    match: [/tibialis anterior/i, /extensor digitorum longus/i, /extensor hallucis longus/i, /fibularis tertius/i, /tibia$/i, /interosseous membrane of .* leg/i],
    context: [/fibula$/i, /fibularis (longus|brevis)/i],
    show: ['skeleton', 'muscles', 'ligaments'], side: 'R', view: { yaw: -0.3, pitch: 0.05, fill: 0.72 }, hotspot: /right tibialis anterior/i,
  },
  achilles: {
    ghost: [/^skin$/i],
    match: [/calcaneal tendon/i, /calcaneus/i, /soleus/i, /gastrocnemius/i, /plantaris/i],
    context: [/tibia$/i, /fibula$/i, /talus/i],
    show: ['skeleton', 'muscles', 'ligaments'], side: 'R', view: { yaw: PI - 0.6, pitch: 0.12, fill: 0.62 }, hotspot: /right calcaneal tendon/i, box: 'achilles',
  },
  ankle: {
    ghost: [/^skin$/i],
    match: [/talofibular/i, /calcaneofibular/i, /deltoid ligament/i, /tibiofibular ligament/i, /talus/i, /fibularis (longus|brevis)/i],
    context: [/tibia$/i, /fibula$/i, /calcaneus/i, /navicular/i, /cuboid/i],
    show: ['skeleton', 'ligaments', 'muscles'], side: 'R', view: { yaw: -1.25, pitch: 0.18, fill: 0.55 }, hotspot: /right talus/i, box: 'ankle',
  },
  foot: {
    ghost: [/^skin$/i],
    match: [/plantar fascia/i, /long plantar ligament/i, /metatarsal/i, /phalanx of .* (toe)/i, /navicular bone of .* foot|cuboid|cuneiform bone|calcaneus|talus|sesamoid bone of .* foot/i, /(abductor hallucis|flexor digitorum brevis|flexor accessorius|of .* foot|flexor hallucis brevis|adductor hallucis|extensor (hallucis|digitorum) brevis)/i],
    show: ['skeleton', 'ligaments', 'muscles'], side: 'R', view: { yaw: -0.9, pitch: -0.35, fill: 0.55 }, hotspot: /right first metatarsal/i,
  },
  heart_lungs: {
    ghost: [/^skin$/i],
    match: [/heart|atrium|ventricle|valve|leaflet|cusp|papillary|interventricular/i, /coronary/i, /trachea/i, /bronch/i, /aorta|pulmonary trunk|pulmonary artery|pulmonary vein|vena cava/i, /lung/i],
    show: ['heart', 'respiratory', 'arteries', 'veins'], side: 'both', view: { yaw: 0.35, pitch: 0.1, fill: 0.6 }, hotspot: /wall of left atrium|wall of ventricle/i, box: 'chest',
  },
  male_repro: {
    ghost: [/^skin$/i, /skin of external genitalia/i, /pubic hair/i, /^scrotum$/i],
    match: [/testis/i, /epididym/i, /deferent duct/i, /seminal vesicle/i, /prostate/i, /corpus cavernosum of penis/i, /corpus spongiosum of penis/i, /glans penis/i, /male urethra/i, /testicular (artery|vein)/i, /dorsal (artery|vein) of penis/i],
    context: [/hip bone/i, /sacrum/i, /urinary bladder/i, /pubic hair/i],
    show: ['skeleton', 'reproductive', 'urinary'], side: 'both', view: { yaw: 0.7, pitch: 0.06, fill: 0.62 }, hotspot: /prostate/i, sex: 'male', box: 'mpelvis',
  },
  female_repro: {
    ghost: [/^skin$/i, /skin of vulva/i, /pubic hair/i, /mons pubis/i],
    match: [/uterus/i, /ovary$/i, /uterine tube/i, /^vagina$/i, /^clitoris$/i, /vestibular (bulb|gland)/i, /labium (minus|majus)/i, /female urethra/i, /round ligament of uterus|ovarian ligament/i],
    context: [/hip bone/i, /sacrum/i, /coccyx/i, /urinary bladder/i, /rectum/i],
    show: ['skeleton', 'reproductive', 'urinary'], side: 'both', view: { yaw: 0.7, pitch: 0.08, fill: 0.62 }, hotspot: /body of uterus/i, sex: 'female', box: 'fpelvis',
  },
  breast: {
    ghost: [/^skin$/i, /breast adipose/i],
    match: [/mammary lobes|lactiferous|nipple|areola|suspensory ligaments of breast/i],
    context: [/pectoralis major/i, /rib$/i, /costal cartilage/i],
    show: ['skeleton', 'muscles', 'reproductive'], side: 'L', view: { yaw: 0.85, pitch: 0.08, fill: 0.5 }, hotspot: /left nipple|nipple/i, sex: 'female', box: 'breast',
  },
  brain: {
    ghost: [/^skin$/i],
    match: [/cerebr|cerebell|gyrus|lobule|lobe$|insula|hippocamp|amygdal|thalam|putamen|pallid|caudate nucleus|corpus callosum|fornix|pons|medulla oblongata|midbrain|ventricle|white matter/i, /optic (nerve|chiasm|tract)/i],
    show: ['nervous'], side: 'both', view: { yaw: 0.75, pitch: 0.2, fill: 0.62 }, hotspot: /white matter of left cerebral hemisphere/i, nervousOnlyBrain: true,
  },
};

export const REGION_GROUPS = [
  { id: 'all', zh: '全部' },
  { id: 'upper', zh: '上肢' },
  { id: 'trunk', zh: '躯干' },
  { id: 'lower', zh: '下肢' },
  { id: 'organs', zh: '器官' },
  { id: 'repro', zh: '生殖' },
];
