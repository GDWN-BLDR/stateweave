// ═══════════════════════════════════════════════════════════
// STATEWEAVE v2 — INTERACTIONS
// ═══════════════════════════════════════════════════════════

// ─── Terminal Typewriter ───
function initTerminal() {
  const textEl = document.getElementById('terminal-text');
  if (!textEl) return;

  const text = 'pip install stateweave';
  let i = 0;

  function type() {
    if (i < text.length) {
      textEl.textContent += text[i];
      i++;
      setTimeout(type, 50 + Math.random() * 40);
    }
  }

  // Start after a brief delay for visual impact
  setTimeout(type, 800);
}

// ─── Nav scroll & mobile toggle ───
function initNav() {
  const nav = document.getElementById('nav');
  const toggle = document.getElementById('nav-toggle');
  const links = document.getElementById('nav-links');
  const progressBar = document.getElementById('scroll-progress');

  // Scroll effect + progress bar
  let ticking = false;
  window.addEventListener('scroll', () => {
    if (!ticking) {
      requestAnimationFrame(() => {
        nav.classList.toggle('scrolled', window.scrollY > 16);

        // Update scroll progress bar
        if (progressBar) {
          const scrollTop = window.scrollY;
          const docHeight = document.documentElement.scrollHeight - window.innerHeight;
          const progress = docHeight > 0 ? (scrollTop / docHeight) * 100 : 0;
          progressBar.style.width = progress + '%';
        }

        ticking = false;
      });
      ticking = true;
    }
  });

  // Mobile toggle
  if (toggle) {
    toggle.addEventListener('click', () => {
      links.classList.toggle('open');
    });
  }

  // Close mobile nav on link click
  links.querySelectorAll('a[href^="#"]').forEach(link => {
    link.addEventListener('click', () => {
      links.classList.remove('open');
    });
  });
}

// ─── Scroll reveal ───
function initReveal() {
  const reveals = document.querySelectorAll('.reveal');
  if (!reveals.length) return;

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.08, rootMargin: '0px 0px -40px 0px' }
  );

  reveals.forEach(el => observer.observe(el));
}

// ─── Code demo tabs ───
function initTabs() {
  const tabs = document.querySelectorAll('.demo-tab');
  const panels = document.querySelectorAll('.demo-panel');
  const filename = document.getElementById('demo-filename');

  const filenames = {
    export: 'export.py',
    import: 'import.py',
    encrypt: 'migrate_encrypted.py',
    diff: 'diff_states.py',
  };

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const target = tab.dataset.tab;

      tabs.forEach(t => t.classList.remove('active'));
      panels.forEach(p => p.classList.remove('active'));

      tab.classList.add('active');
      document.getElementById(`panel-${target}`).classList.add('active');

      if (filename) filename.textContent = filenames[target] || '';
    });
  });
}

// ─── Copy buttons ───
function initCopy() {
  document.querySelectorAll('.copy-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const text = btn.dataset.copy;
      if (!text) return;

      try {
        await navigator.clipboard.writeText(text);
        btn.classList.add('copied');
        const svg = btn.querySelector('svg');
        if (svg) {
          const original = svg.innerHTML;
          svg.innerHTML = '<polyline points="20 6 9 17 4 12" stroke="currentColor" stroke-width="2" fill="none"/>';
          setTimeout(() => {
            svg.innerHTML = original;
            btn.classList.remove('copied');
          }, 1500);
        }
      } catch {
        // Fallback: select text
      }
    });
  });
}

// ─── FAQ accordion ───
function initFAQ() {
  document.querySelectorAll('.faq-question').forEach(btn => {
    btn.addEventListener('click', () => {
      const item = btn.closest('.faq-item');
      const answer = item.querySelector('.faq-answer');
      const isOpen = item.classList.contains('open');

      // Close all
      document.querySelectorAll('.faq-item.open').forEach(openItem => {
        openItem.classList.remove('open');
        openItem.querySelector('.faq-answer').style.maxHeight = '0';
      });

      // Open clicked (if it wasn't already open)
      if (!isOpen) {
        item.classList.add('open');
        answer.style.maxHeight = answer.scrollHeight + 'px';
      }
    });
  });
}

// ─── Smooth scroll ───
function initSmoothScroll() {
  document.querySelectorAll('a[href^="#"]').forEach(link => {
    link.addEventListener('click', (e) => {
      const targetId = link.getAttribute('href');
      if (targetId === '#') return;
      const target = document.querySelector(targetId);
      if (!target) return;

      e.preventDefault();
      const offset = 56 + 20; // nav height + padding
      const y = target.getBoundingClientRect().top + window.pageYOffset - offset;

      window.scrollTo({ top: y, behavior: 'smooth' });
    });
  });
}

// ─── GitHub stars (graceful fail) ───
async function fetchStars() {
  try {
    const res = await fetch('https://api.github.com/repos/GDWN-BLDR/stateweave');
    if (!res.ok) return;
    const data = await res.json();
    const el = document.getElementById('star-count');
    if (el && data.stargazers_count != null) {
      el.textContent = formatNumber(data.stargazers_count);
    }
  } catch {
    // Silently fail — star count is optional
  }
}

function formatNumber(n) {
  if (n >= 1000) return (n / 1000).toFixed(1) + 'k';
  return String(n);
}

// ─── Init ───
document.addEventListener('DOMContentLoaded', () => {
  initTerminal();
  initNav();
  initReveal();
  initTabs();
  initCopy();
  initFAQ();
  initSmoothScroll();
  fetchStars();
});
