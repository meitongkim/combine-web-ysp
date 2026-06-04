/**
 * BibLabU LMS — Client-side JavaScript
 * Handles: scroll reveals, magnetic buttons, sidebar toggle, toasts, counters, modals
 */

(function () {
  "use strict";

  // ─── Nav scroll state + Hero parallax ──────────────────────────────────
  const navWrap = document.getElementById("navWrap");
  const heroBg = document.getElementById("heroBg");
  let lastScroll = -1;

  function onScroll() {
    const y = window.scrollY || window.pageYOffset;
    if (y === lastScroll) return;
    lastScroll = y;
    if (navWrap) {
      if (y > 40) navWrap.classList.add("scrolled");
      else navWrap.classList.remove("scrolled");
    }
    if (heroBg) {
      heroBg.style.transform = "translate3d(0," + y * 0.25 + "px,0)";
    }
  }
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  // ─── Apple-style scroll reveals (IntersectionObserver) ─────────────────
  const revealObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((en) => {
        if (en.isIntersecting) {
          en.target.classList.add("is-in");
          revealObserver.unobserve(en.target);
        }
      });
    },
    { threshold: 0.12, rootMargin: "0px 0px -6% 0px" }
  );

  document
    .querySelectorAll(
      ".apple-reveal, .apple-scale, .apple-slide-left, .apple-slide-right"
    )
    .forEach((el) => revealObserver.observe(el));

  // ─── Magnetic buttons ──────────────────────────────────────────────────
  document.querySelectorAll("[data-magnetic]").forEach((el) => {
    let raf = null, tx = 0, ty = 0, cx = 0, cy = 0;
    const STR = 14;

    function loop() {
      tx += (cx - tx) * 0.18;
      ty += (cy - ty) * 0.18;
      el.style.transform =
        "translate(" + tx.toFixed(2) + "px," + ty.toFixed(2) + "px)";
      if (Math.abs(cx - tx) > 0.05 || Math.abs(cy - ty) > 0.05) {
        raf = requestAnimationFrame(loop);
      } else {
        raf = null;
      }
    }

    el.addEventListener("mousemove", (e) => {
      const r = el.getBoundingClientRect();
      const dx = (e.clientX - (r.left + r.width / 2)) / (r.width / 2);
      const dy = (e.clientY - (r.top + r.height / 2)) / (r.height / 2);
      cx = dx * STR;
      cy = dy * STR;
      if (!raf) raf = requestAnimationFrame(loop);
    });

    el.addEventListener("mouseleave", () => {
      cx = 0;
      cy = 0;
      if (!raf) raf = requestAnimationFrame(loop);
    });
  });

  // ─── Animated counters ─────────────────────────────────────────────────
  const easeOutCubic = (t) => 1 - Math.pow(1 - t, 3);
  const counterObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((en) => {
        if (!en.isIntersecting) return;
        counterObserver.unobserve(en.target);
        const el = en.target;
        const target = parseInt(el.getAttribute("data-counter"), 10);
        const dur = 1600;
        const t0 = performance.now();

        function tick(now) {
          const t = Math.min(1, (now - t0) / dur);
          el.textContent = Math.round(easeOutCubic(t) * target).toLocaleString();
          if (t < 1) requestAnimationFrame(tick);
          else el.textContent = target.toLocaleString();
        }
        requestAnimationFrame(tick);
      });
    },
    { threshold: 0.4 }
  );

  document
    .querySelectorAll("[data-counter]")
    .forEach((el) => counterObserver.observe(el));

  // ─── Toast auto-dismiss ────────────────────────────────────────────────
  document.querySelectorAll(".toast").forEach((toast) => {
    // Auto dismiss after 5 seconds
    const timer = setTimeout(() => dismissToast(toast), 5000);

    // Close button
    const closeBtn = toast.querySelector(".toast-close");
    if (closeBtn) {
      closeBtn.addEventListener("click", () => {
        clearTimeout(timer);
        dismissToast(toast);
      });
    }
  });

  function dismissToast(toast) {
    toast.classList.add("toast-out");
    toast.addEventListener("animationend", () => toast.remove(), { once: true });
  }

  // ─── Mobile sidebar toggle ────────────────────────────────────────────
  const sidebarToggle = document.getElementById("sidebarToggle");
  const sidebar = document.getElementById("sidebar");

  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener("click", () => {
      sidebar.classList.toggle("open");
      // Update icon
      const icon = sidebarToggle.querySelector("span");
      if (icon) {
        icon.textContent = sidebar.classList.contains("open") ? "✕" : "☰";
      }
    });

    // Close sidebar on click outside (mobile)
    document.addEventListener("click", (e) => {
      if (
        sidebar.classList.contains("open") &&
        !sidebar.contains(e.target) &&
        !sidebarToggle.contains(e.target)
      ) {
        sidebar.classList.remove("open");
        const icon = sidebarToggle.querySelector("span");
        if (icon) icon.textContent = "☰";
      }
    });
  }

  // ─── Confirm delete dialogs ───────────────────────────────────────────
  document.querySelectorAll("[data-confirm]").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      const msg = btn.getAttribute("data-confirm") || "Are you sure?";
      if (!confirm(msg)) {
        e.preventDefault();
      }
    });
  });

  // ─── File upload preview ──────────────────────────────────────────────
  document.querySelectorAll(".file-upload-trigger").forEach((trigger) => {
    const input = trigger.querySelector('input[type="file"]');
    const label = trigger.querySelector(".file-label");

    if (input && label) {
      input.addEventListener("change", () => {
        if (input.files.length > 0) {
          const file = input.files[0];
          const sizeMB = (file.size / (1024 * 1024)).toFixed(1);
          label.textContent = `${file.name} (${sizeMB} MB)`;
          label.style.color = "var(--sage-deep)";
        } else {
          label.textContent = "Choose a file or drag it here";
          label.style.color = "";
        }
      });
    }
  });

  // ─── Form validation visual feedback ──────────────────────────────────
  document.querySelectorAll("form[data-validate]").forEach((form) => {
    form.addEventListener("submit", (e) => {
      let valid = true;
      form.querySelectorAll("[required]").forEach((input) => {
        if (!input.value.trim()) {
          input.style.borderColor = "var(--error)";
          valid = false;
        } else {
          input.style.borderColor = "";
        }
      });

      // Password confirmation
      const pass = form.querySelector('input[name="password"]');
      const confirm = form.querySelector('input[name="confirm_password"]');
      if (pass && confirm && pass.value !== confirm.value) {
        confirm.style.borderColor = "var(--error)";
        valid = false;
      }

      if (!valid) {
        e.preventDefault();
      }
    });
  });

  // ─── Stagger animation on card grids ──────────────────────────────────
  const gridObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((en) => {
        if (en.isIntersecting) {
          const cards = en.target.querySelectorAll(".module-card, .stat-card, .announcement-card");
          cards.forEach((card, i) => {
            card.style.transitionDelay = `${i * 0.06}s`;
            card.classList.add("is-in");
          });
          gridObserver.unobserve(en.target);
        }
      });
    },
    { threshold: 0.1 }
  );

  document.querySelectorAll(".module-grid, .stats-grid").forEach((grid) => {
    gridObserver.observe(grid);
  });

  // Mobile Menu Toggle (Hamburger)
  const menuToggle = document.getElementById("menuToggle");
  const nav = document.querySelector(".nav");
  if (menuToggle && nav) {
    menuToggle.addEventListener("click", (e) => {
      e.stopPropagation();
      nav.classList.toggle("menu-open");
    });
    document.addEventListener("click", (e) => {
      if (!nav.contains(e.target)) {
        nav.classList.remove("menu-open");
      }
    });
  }

  // ─── Language Selector Interactivity & Cookie Management ───────────────
  const langSelector = document.getElementById("langSelector");
  const langBtn = document.getElementById("langBtn");
  const currentLangText = document.getElementById("currentLangText");

  if (langSelector && langBtn) {
    // Helper to read cookies
    function getCookie(name) {
      const value = `; ${document.cookie}`;
      const parts = value.split(`; ${name}=`);
      if (parts.length === 2) return parts.pop().split(';').shift();
    }

    // Helper to set cookies
    function setCookie(name, value, days) {
      let expires = "";
      if (days) {
        const date = new Date();
        date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
        expires = "; expires=" + date.toUTCString();
      }
      document.cookie = `${name}=${value || ""}${expires}; path=/;`;
      document.cookie = `${name}=${value || ""}${expires}; path=/; domain=${window.location.hostname};`;
    }

    // Helper to delete cookies
    function deleteCookie(name) {
      document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
      document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; domain=${window.location.hostname};`;
    }

    // Determine current language from googtrans cookie (e.g. "/en/es" or "/auto/es")
    const transCookie = getCookie("googtrans");
    let currentLang = "en";

    if (transCookie) {
      const parts = transCookie.split("/");
      if (parts.length >= 3) {
        currentLang = parts[2];
      }
    }

    // Update dropdown selection classes and UI text based on active cookie
    const langOptions = langSelector.querySelectorAll(".lang-option");
    let selectedOptionFound = false;

    langOptions.forEach((option) => {
      const optLang = option.getAttribute("data-lang");
      if (optLang === currentLang) {
        option.classList.add("active");
        if (currentLangText) {
          // Keep only the text (slice after emoji space)
          const textContent = option.textContent.trim();
          const words = textContent.split(" ");
          // "🇺🇸 English" -> "English"
          currentLangText.textContent = words.slice(1).join(" ");
        }
        selectedOptionFound = true;
      } else {
        option.classList.remove("active");
      }
    });

    if (!selectedOptionFound && currentLang === "en" && currentLangText) {
      currentLangText.textContent = "English";
    }

    // Toggle dropdown menu display
    langBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      const isOpen = langSelector.classList.toggle("open");
      langBtn.setAttribute("aria-expanded", isOpen);
    });

    // Close dropdown on click outside
    document.addEventListener("click", (e) => {
      if (!langSelector.contains(e.target)) {
        langSelector.classList.remove("open");
        langBtn.setAttribute("aria-expanded", "false");
      }
    });

    // Listen to option selections
    langOptions.forEach((option) => {
      option.addEventListener("click", (e) => {
        e.stopPropagation();
        const selectedLang = option.getAttribute("data-lang");

        if (selectedLang === "en") {
          deleteCookie("googtrans");
        } else {
          // Set googtrans cookie to auto translate
          setCookie("googtrans", `/en/${selectedLang}`, 30);
        }

        langSelector.classList.remove("open");
        langBtn.setAttribute("aria-expanded", "false");
        
        // Force reload to apply Google Translate dynamically
        window.location.reload();
      });
    });
  }
})();
