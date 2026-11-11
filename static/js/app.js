(function () {
  "use strict";

  function addHours(value, hours) {
    if (!value || value.indexOf(":") === -1) return "";
    var parts = value.split(":");
    var total = parseInt(parts[0], 10) * 60 + parseInt(parts[1], 10) + hours * 60;
    if (total >= 23 * 60 + 59) total = 23 * 60;
    var hh = Math.floor(total / 60);
    var mm = total % 60;
    return String(hh).padStart(2, "0") + ":" + String(mm).padStart(2, "0");
  }

  document.addEventListener("DOMContentLoaded", function () {
    var navToggle = document.getElementById("navToggle");
    var navMenu = document.getElementById("navMenu");
    if (navToggle && navMenu) {
      navToggle.addEventListener("click", function () {
        var open = navMenu.classList.toggle("open");
        navToggle.setAttribute("aria-expanded", open ? "true" : "false");
      });
      navMenu.addEventListener("click", function (event) {
        if (event.target.closest("a")) {
          navMenu.classList.remove("open");
          navToggle.setAttribute("aria-expanded", "false");
        }
      });
    }

    var heroSlides = document.querySelectorAll("#heroSlideshow .hero-slide");
    if (heroSlides.length > 1) {
      var heroIndex = 0;
      var heroTimer = null;

      function advanceHero() {
        heroSlides[heroIndex].classList.remove("is-active");
        heroIndex = (heroIndex + 1) % heroSlides.length;
        var nextSlide = heroSlides[heroIndex];
        void nextSlide.offsetWidth;
        nextSlide.classList.add("is-active");
      }

      function startHero() {
        window.clearInterval(heroTimer);
        heroTimer = window.setInterval(advanceHero, 2000);
      }

      startHero();
      document.addEventListener("visibilitychange", function () {
        if (document.hidden) {
          window.clearInterval(heroTimer);
        } else {
          startHero();
        }
      });
    }

    var liveSlides = document.querySelectorAll(".hero-live-slide");
    var liveDots = document.querySelectorAll("#heroLiveDots span");
    var liveBoard = document.querySelector(".mock-board");
    if (liveSlides.length > 1) {
      var liveIndex = 0;
      var liveTimer = null;

      function showLiveSlide(index) {
        liveSlides[liveIndex].classList.remove("is-active");
        if (liveDots[liveIndex]) liveDots[liveIndex].classList.remove("active");
        liveIndex = index;
        liveSlides[liveIndex].classList.add("is-active");
        if (liveDots[liveIndex]) liveDots[liveIndex].classList.add("active");
      }

      function nextLiveSlide() {
        showLiveSlide((liveIndex + 1) % liveSlides.length);
      }

      function startLiveSlides() {
        window.clearInterval(liveTimer);
        liveTimer = window.setInterval(nextLiveSlide, 3500);
      }

      startLiveSlides();
      if (liveBoard) {
        liveBoard.addEventListener("mouseenter", function () {
          window.clearInterval(liveTimer);
        });
        liveBoard.addEventListener("mouseleave", startLiveSlides);
      }
    }

    var liveRows = document.querySelectorAll(".hero-live-row");
    if (liveRows.length) {
      function refreshHeroAvailability() {
        fetch("/api/hero-availability", { cache: "no-store" })
          .then(function (response) { return response.ok ? response.json() : null; })
          .then(function (data) {
            if (!data || !data.rooms) return;
            var byId = {};
            data.rooms.forEach(function (room) { byId[room.id] = room; });
            liveRows.forEach(function (row) {
              var room = byId[parseInt(row.getAttribute("data-room-id"), 10)];
              if (!room) return;
              var badge = row.querySelector(".mock-status");
              var detail = row.querySelector(".mock-room small");
              if (badge) {
                badge.textContent = room.label;
                badge.classList.toggle("ok", room.status === "kosong");
                badge.classList.toggle("fill", room.status !== "kosong");
              }
              if (detail) {
                detail.textContent = room.gedung + " · Lt. " + room.lantai + " · " + room.detail;
              }
            });
            var stamp = document.getElementById("heroLiveStamp");
            if (stamp) stamp.textContent = "live · " + data.generated_at;
          })
          .catch(function () {});
      }

      window.setInterval(refreshHeroAvailability, 15000);
    }

    document.querySelectorAll(".toast").forEach(function (toast) {
      var close = toast.querySelector(".toast-close");
      function remove() {
        toast.style.opacity = "0";
        toast.style.transform = "translateY(-6px)";
        window.setTimeout(function () { toast.remove(); }, 180);
      }
      if (close) close.addEventListener("click", remove);
      window.setTimeout(remove, 6500);
    });

    document.querySelectorAll("[data-print]").forEach(function (button) {
      button.addEventListener("click", function () { window.print(); });
    });

    document.querySelectorAll(".demo-account").forEach(function (button) {
      button.addEventListener("click", function () {
        var email = document.querySelector('input[name="email"]');
        var password = document.querySelector('input[name="password"]');
        if (email) email.value = button.getAttribute("data-email") || "";
        if (password) password.value = button.getAttribute("data-password") || "";
        if (email) email.focus();
      });
    });

    document.querySelectorAll('input[type="date"]').forEach(function (input) {
      if (!input.min) {
        var today = new Date();
        var iso = today.getFullYear() + "-" + String(today.getMonth() + 1).padStart(2, "0") + "-" + String(today.getDate()).padStart(2, "0");
        input.min = iso;
      }
    });

    function bindTimePair(startId, endId) {
      var start = document.getElementById(startId);
      var end = document.getElementById(endId);
      if (!start || !end) return;
      start.addEventListener("change", function () {
        if (!start.value) return;
        var suggested = addHours(start.value, 2);
        if (!end.value || end.value <= start.value) end.value = suggested;
      });
    }
    bindTimePair("searchMulai", "searchSelesai");
    bindTimePair("bookingMulai", "bookingSelesai");

    var fileInput = document.getElementById("dokumen");
    var fileName = document.getElementById("uploadName");
    if (fileInput && fileName) {
      fileInput.addEventListener("change", function () {
        var name = fileInput.files && fileInput.files[0] ? fileInput.files[0].name : "Belum ada file";
        fileName.textContent = name;
      });
    }

    var bookingForm = document.getElementById("bookingForm");
    if (bookingForm) {
      bookingForm.addEventListener("submit", function () {
        var submit = document.getElementById("bookingSubmit");
        if (submit) {
          submit.disabled = true;
          submit.textContent = "Memproses alokasi…";
        }
      });
    }
  });
})();
