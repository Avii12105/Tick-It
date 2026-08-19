(function () {
    "use strict";

    var prefersReducedMotion = window.matchMedia(
        "(prefers-reduced-motion: reduce)"
    ).matches;

    // Cursor-reactive parallax — drives --mx / --my used by .cursor-glow
    // and the aurora blobs.
    var glow = document.querySelector(".cursor-glow");
    var aurora = document.querySelector(".bg-aurora");
    var blobs = document.querySelectorAll(".blob");
    var root = document.documentElement;

    function onPointerMove(e) {
        var x = e.clientX / window.innerWidth - 0.5;
        var y = e.clientY / window.innerHeight - 0.5;
        root.style.setProperty("--mx", x.toFixed(3));
        root.style.setProperty("--my", y.toFixed(3));

        if (prefersReducedMotion) return;

        if (aurora) {
            aurora.style.transform =
                "translate(" + (x * 8) + "px, " + (y * 8) + "px)";
        }
        blobs.forEach(function (blob, i) {
            var depth = 14 + i * 6;
            blob.style.transform =
                "translate(" + x * depth + "px, " + y * depth + "px)";
        });
    }

    // Glass tilt — rotate cards toward the cursor (skip on reduced motion).
    function attachTilt(card) {
        if (prefersReducedMotion) return;

        card.addEventListener("pointermove", function (e) {
            var rect = card.getBoundingClientRect();
            var px = (e.clientX - rect.left) / rect.width;
            var py = (e.clientY - rect.top) / rect.height;
            var rx = (0.5 - py) * 10;
            var ry = (px - 0.5) * 12;
            card.style.transform =
                "perspective(900px) rotateX(" +
                rx.toFixed(2) +
                "deg) rotateY(" +
                ry.toFixed(2) +
                "deg) translateY(-4px)";
        });

        card.addEventListener("pointerleave", function () {
            card.style.transform = "";
        });
    }

    function init() {
        document.addEventListener("pointermove", onPointerMove, {
            passive: true,
        });
        document.querySelectorAll(".tilt").forEach(attachTilt);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();