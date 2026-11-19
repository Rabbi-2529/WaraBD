/* =========================================================
   WaRa BD — product catalog
   To add a product: copy the object below, give it a unique
   `id`, and fill in its details. It then appears on the
   Products page and gets its own page at product.html?id=<id>.
   Optional sections (highlights, description, specs, features,
   applications, steps, faq) are hidden when left out.
   `stock` is one of: 'in-stock' | 'out-of-stock' | 'upcoming'.
   ========================================================= */
window.WARA_PRODUCTS = (function () {
  const IMG = 'https://admin.felnatech.com/storage/app/public/products/';

  return [
    {
      id: 'ft-scl029',
      featured: true, // shown on the home and portfolio pages
      brand: 'WaRa',
      category: 'Smart Cabinet Lock',
      name: 'WaRa FT-SCL029 Cabinet Drawer Lock',
      subtitle: 'With Visitor Password Changing Access',
      model: 'FT-SCL029',
      sku: 'WR-SCL029-BK',
      color: 'Black',
      price: 1975,
      oldPrice: 2050,
      stock: 'in-stock',
      warranty: '1 Year',
      added: '2026-10-22',
      short: 'A compact round keypad and a motorized lock body that turn any cabinet, drawer, wardrobe or locker into keyless, code-protected storage.',
      // Swap these for local files (e.g. assets/img/ft-scl029-1.jpg) any time
      images: [
        { src: IMG + 'ft-scl029-felnatech-6609-ft.jpg', caption: 'Round keypad & motorized lock body' },
        { src: IMG + 'ft-scl029-felnatech-6609-1.jpg', caption: 'Compact keypad — fits in your palm' },
        { src: IMG + 'ft-scl029-felnatech-6609-2.jpg', caption: 'Front-mounted keypad on a cabinet door' },
        { src: IMG + 'ft-scl029-felnatech-6609-3.jpg', caption: 'Installed on wardrobe cabinets' }
      ],
      highlights: [
        'Password & USB key unlock',
        'Management + user codes',
        'Public (visitor) & private modes',
        '1 main + 3 management USB keys',
        'Low-battery reminder',
        'USB emergency power'
      ],
      descriptionTitle: 'Keyless, code-protected storage for anything with a door',
      description: [
        'The WaRa FT-SCL029 replaces the old key-and-cylinder cabinet lock with a slim round keypad. The keypad sits on the outside of the door; a motorized lock body mounts neatly inside, so there\'s nothing to pick and no key to lose.',
        'Two password levels keep control in the right hands: a <strong>management code</strong> for the owner and a <strong>user code</strong> for everyday access. Switch to <strong>public mode</strong> and each visitor sets their own code — ideal for gyms, spas, hotels, schools and shared offices.',
        'For backup, the lock supports one main USB key and three management USB keys. Low power consumption gives long battery life, a low-battery reminder warns you in good time, and an external USB emergency power port means you\'re never locked out.'
      ],
      tags: ['FCC', 'CE', 'RoHS', 'Motorized lock'],
      specs: [
        ['Model', 'FT-SCL029'],
        ['Brand', 'WaRa'],
        ['Type', 'Furniture / cabinet & drawer lock'],
        ['Unlock methods', 'Password, USB key'],
        ['Password sets', 'Management code + user code'],
        ['USB key management', '1 main key + 3 management keys'],
        ['Usage modes', 'Public (visitor) mode & private mode'],
        ['Locking system', 'Motorized mechanism'],
        ['Front body (keypad)', 'Ø 50.5 mm × 12.5 mm'],
        ['Back body (lock)', '60 × 86 × 23.5 mm (W × H × D)'],
        ['Suitable door thickness', 'More than 3 mm'],
        ['Housing material', 'ABS'],
        ['Power', 'Low power consumption, low-battery reminder, external USB emergency power'],
        ['Color', 'Black'],
        ['Design style', 'Minimalist'],
        ['Certification', 'FCC, CE, RoHS'],
        ['Compatible with', 'Cabinets, drawers, wardrobes, lockers'],
        ['Warranty', '1 Year']
      ],
      features: [
        { icon: 'keypad', title: 'Two password sets', text: 'A management code for the owner and a user code for daily access.' },
        { icon: 'users', title: 'Visitor password changing', text: 'In public mode each visitor sets their own one-time code.' },
        { icon: 'usb', title: 'USB key management', text: 'One main key plus three management keys for backup control.' },
        { icon: 'lock', title: 'Motorized mechanism', text: 'Smooth, quiet electric locking with no exposed key cylinder.' },
        { icon: 'battery', title: 'Low power, long life', text: 'Low power consumption with a reminder before the battery runs low.' },
        { icon: 'zap', title: 'USB emergency power', text: 'Plug in external USB power to open the lock even with flat batteries.' }
      ],
      applications: {
        compatible: ['Cabinets', 'Drawers', 'Wardrobes', 'Lockers'],
        places: ['Kitchen', 'Bathroom', 'Living room', 'Bedroom', 'Dining', 'Hotel', 'Office building', 'Hospital', 'School', 'Mall', 'Sports venues', 'Leisure facilities', 'Supermarket', 'Warehouse', 'Workshop', 'Storage & closet', 'Wine cellar', 'Gym']
      },
      steps: [
        { title: 'Mount it', text: 'Fix the keypad on the front and screw the lock body inside a door thicker than 3 mm.' },
        { title: 'Set your codes', text: 'Create the management code first, then add a user code for daily use.' },
        { title: 'Pick a mode', text: 'Public mode for visitors, private mode for a fixed personal code.' },
        { title: 'Tap & open', text: 'Enter the code and the motor unlocks. USB keys and USB power are your backup.' }
      ],
      faq: [
        { q: 'What is the difference between public and private mode?', a: 'In <strong>public mode</strong> each visitor sets their own code when they lock, and it is released once they unlock — perfect for gyms, hotels and shared lockers. In <strong>private mode</strong> the lock keeps one fixed user code, ideal for your own cabinet or office drawer.' },
        { q: 'What happens if the battery runs out?', a: 'The lock warns you with a low-battery reminder well before it runs flat. If it does run out, connect external USB power (for example a power bank) to the emergency port and open it with your code.' },
        { q: 'I forgot the user code. Can I still open it?', a: 'Yes. The management code or one of the USB management keys can open the lock, after which you can set a new user code.' },
        { q: 'Will it fit my cabinet or drawer?', a: 'The keypad is Ø 50.5 mm on the front and the lock body is 60 × 86 × 23.5 mm inside. It suits doors and drawer fronts thicker than 3 mm. Send us a photo on WhatsApp if you are unsure.' },
        { q: 'Do I need an electrician to install it?', a: 'No. There is no mains wiring — you only need a drill and a screwdriver. Our team can guide you over phone or WhatsApp.' },
        { q: 'How can I pay?', a: 'Cash on delivery anywhere in Bangladesh, or pay in advance with bKash or Nagad at checkout.' }
      ]
    }
  ];
})();
