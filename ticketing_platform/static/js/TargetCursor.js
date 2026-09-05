/**
 * TargetCursor — Vanilla JS port of the React Bits TargetCursor component
 * Dependencies: GSAP (dynamically loaded via CDN if not already on window)
 *
 * Usage:
 *   import { mountTargetCursor } from '/static/js/TargetCursor.js';
 *   const destroy = await mountTargetCursor({
 *     targetSelector: '.cursor-target',
 *     spinDuration: 2,
 *     hideDefaultCursor: true,
 *     parallaxOn: true,
 *     cursorColor: '#ffffff',
 *     cursorColorOnTarget: '#F7AA28'
 *   });
 */

async function loadGsap() {
  if (window.gsap) return window.gsap;
  try {
    const mod = await import('https://cdn.jsdelivr.net/npm/gsap@3.12.5/index.js');
    return mod.gsap || mod.default || window.gsap;
  } catch (err) {
    return new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = 'https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js';
      script.onload = () => resolve(window.gsap);
      script.onerror = reject;
      document.head.appendChild(script);
    });
  }
}

const getContainingBlock = element => {
  let node = element?.parentElement;
  while (node && node !== document.documentElement) {
    const style = getComputedStyle(node);
    if (
      style.transform !== 'none' ||
      style.perspective !== 'none' ||
      style.filter !== 'none' ||
      style.willChange.includes('transform') ||
      style.willChange.includes('perspective') ||
      style.willChange.includes('filter') ||
      /paint|layout|strict|content/.test(style.contain)
    ) {
      return node;
    }
    node = node.parentElement;
  }
  return null;
};

const getContainingBlockOffset = block => {
  if (!block) return { x: 0, y: 0 };
  const rect = block.getBoundingClientRect();
  return { x: rect.left + block.clientLeft, y: rect.top + block.clientTop };
};

/**
 * Mount TargetCursor to document.body
 * @param {object} opts
 * @returns {Promise<function>} cleanup function
 */
export async function mountTargetCursor(opts = {}) {
  const {
    targetSelector = '.cursor-target',
    spinDuration = 2,
    hideDefaultCursor = true,
    hoverDuration = 0.2,
    parallaxOn = true,
    cursorColor = '#ffffff',
    cursorColorOnTarget
  } = opts;

  if (typeof window === 'undefined' || typeof document === 'undefined') {
    return () => {};
  }

  const hasTouchScreen = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
  const isSmallScreen = window.innerWidth <= 768;
  const userAgent = navigator.userAgent || navigator.vendor || window.opera;
  const mobileRegex = /android|webos|iphone|ipad|ipod|blackberry|iemobile|opera mini/i;
  const isMobileUserAgent = mobileRegex.test(userAgent.toLowerCase());
  const isMobile = (hasTouchScreen && isSmallScreen) || isMobileUserAgent;

  if (isMobile) {
    return () => {};
  }

  const gsap = await loadGsap();
  if (!gsap) {
    console.warn('[TargetCursor] GSAP failed to load.');
    return () => {};
  }

  const constants = {
    borderWidth: 3,
    cornerSize: 12
  };

  // Build DOM structure
  const cursor = document.createElement('div');
  cursor.className = 'target-cursor-wrapper';

  const dot = document.createElement('div');
  dot.className = 'target-cursor-dot';
  dot.style.backgroundColor = cursorColor;
  cursor.appendChild(dot);

  const cornerClasses = ['corner-tl', 'corner-tr', 'corner-br', 'corner-bl'];
  const corners = cornerClasses.map(cls => {
    const c = document.createElement('div');
    c.className = `target-cursor-corner ${cls}`;
    c.style.borderColor = cursorColor;
    cursor.appendChild(c);
    return c;
  });

  document.body.appendChild(cursor);

  const originalCursor = document.body.style.cursor;
  if (hideDefaultCursor) {
    document.body.style.cursor = 'none';
  }

  let containingBlock = getContainingBlock(cursor);
  const getOffset = () => getContainingBlockOffset(containingBlock);

  let activeTarget = null;
  let currentLeaveHandler = null;
  let resumeTimeout = null;
  let isActive = false;
  let targetCornerPositions = null;
  const activeStrength = { current: 0 };

  const cleanupTarget = target => {
    if (currentLeaveHandler) {
      target.removeEventListener('mouseleave', currentLeaveHandler);
    }
    currentLeaveHandler = null;
  };

  const initialOffset = getOffset();
  gsap.set(cursor, {
    xPercent: -50,
    yPercent: -50,
    x: window.innerWidth / 2 - initialOffset.x,
    y: window.innerHeight / 2 - initialOffset.y
  });

  let spinTl = null;
  const createSpinTimeline = () => {
    if (spinTl) spinTl.kill();
    spinTl = gsap
      .timeline({ repeat: -1 })
      .to(cursor, { rotation: '+=360', duration: spinDuration, ease: 'none' });
  };
  createSpinTimeline();

  const moveCursor = (x, y) => {
    if (!cursor) return;
    const { x: offsetX, y: offsetY } = getOffset();
    gsap.to(cursor, {
      x: x - offsetX,
      y: y - offsetY,
      duration: 0.1,
      ease: 'power3.out'
    });
  };

  const tickerFn = () => {
    if (!targetCornerPositions || !cursor || !corners.length) return;
    const strength = activeStrength.current;
    if (strength === 0) return;

    const cursorX = gsap.getProperty(cursor, 'x');
    const cursorY = gsap.getProperty(cursor, 'y');

    corners.forEach((corner, i) => {
      const currentX = gsap.getProperty(corner, 'x');
      const currentY = gsap.getProperty(corner, 'y');

      const targetX = targetCornerPositions[i].x - cursorX;
      const targetY = targetCornerPositions[i].y - cursorY;

      const finalX = currentX + (targetX - currentX) * strength;
      const finalY = currentY + (targetY - currentY) * strength;

      const duration = strength >= 0.99 ? (parallaxOn ? 0.2 : 0) : 0.05;

      gsap.to(corner, {
        x: finalX,
        y: finalY,
        duration: duration,
        ease: duration === 0 ? 'none' : 'power1.out',
        overwrite: 'auto'
      });
    });
  };

  const moveHandler = e => moveCursor(e.clientX, e.clientY);
  window.addEventListener('mousemove', moveHandler);

  const scrollHandler = () => {
    if (!activeTarget || !cursor) return;
    const { x: offsetX, y: offsetY } = getOffset();
    const mouseX = gsap.getProperty(cursor, 'x') + offsetX;
    const mouseY = gsap.getProperty(cursor, 'y') + offsetY;
    const elementUnderMouse = document.elementFromPoint(mouseX, mouseY);
    const isStillOverTarget =
      elementUnderMouse &&
      (elementUnderMouse === activeTarget || elementUnderMouse.closest(targetSelector) === activeTarget);
    if (!isStillOverTarget) {
      if (currentLeaveHandler) {
        currentLeaveHandler();
      }
    }
  };
  window.addEventListener('scroll', scrollHandler, { passive: true });

  const mouseDownHandler = () => {
    if (!dot) return;
    gsap.to(dot, { scale: 0.7, duration: 0.3 });
    gsap.to(cursor, { scale: 0.9, duration: 0.2 });
  };

  const mouseUpHandler = () => {
    if (!dot) return;
    gsap.to(dot, { scale: 1, duration: 0.3 });
    gsap.to(cursor, { scale: 1, duration: 0.2 });
  };

  window.addEventListener('mousedown', mouseDownHandler);
  window.addEventListener('mouseup', mouseUpHandler);

  const enterHandler = e => {
    const directTarget = e.target;
    const allTargets = [];
    let current = directTarget;
    while (current && current !== document.body) {
      if (current.matches && current.matches(targetSelector)) {
        allTargets.push(current);
      }
      current = current.parentElement;
    }
    const target = allTargets[0] || null;
    if (!target || !cursor || !corners.length) return;
    if (activeTarget === target) return;
    if (activeTarget) {
      cleanupTarget(activeTarget);
    }
    if (resumeTimeout) {
      clearTimeout(resumeTimeout);
      resumeTimeout = null;
    }

    activeTarget = target;
    corners.forEach(corner => gsap.killTweensOf(corner, 'x,y'));

    gsap.killTweensOf(cursor, 'rotation');
    spinTl?.pause();
    gsap.set(cursor, { rotation: 0 });

    if (cursorColorOnTarget) {
      gsap.to(corners, {
        borderColor: cursorColorOnTarget,
        duration: 0.15,
        ease: 'power2.out'
      });
      if (dot) {
        gsap.to(dot, {
          backgroundColor: cursorColorOnTarget,
          duration: 0.15,
          ease: 'power2.out'
        });
      }
    }

    const rect = target.getBoundingClientRect();
    const { borderWidth, cornerSize } = constants;
    const { x: offsetX, y: offsetY } = getOffset();
    const cursorX = gsap.getProperty(cursor, 'x');
    const cursorY = gsap.getProperty(cursor, 'y');

    targetCornerPositions = [
      { x: rect.left - borderWidth - offsetX, y: rect.top - borderWidth - offsetY },
      { x: rect.right + borderWidth - cornerSize - offsetX, y: rect.top - borderWidth - offsetY },
      { x: rect.right + borderWidth - cornerSize - offsetX, y: rect.bottom + borderWidth - cornerSize - offsetY },
      { x: rect.left - borderWidth - offsetX, y: rect.bottom + borderWidth - cornerSize - offsetY }
    ];

    isActive = true;
    gsap.ticker.add(tickerFn);

    gsap.to(activeStrength, {
      current: 1,
      duration: hoverDuration,
      ease: 'power2.out'
    });

    corners.forEach((corner, i) => {
      gsap.to(corner, {
        x: targetCornerPositions[i].x - cursorX,
        y: targetCornerPositions[i].y - cursorY,
        duration: 0.2,
        ease: 'power2.out'
      });
    });

    const leaveHandler = () => {
      gsap.ticker.remove(tickerFn);

      isActive = false;
      targetCornerPositions = null;
      gsap.set(activeStrength, { current: 0, overwrite: true });
      activeTarget = null;

      if (cursorColorOnTarget) {
        gsap.to(corners, {
          borderColor: cursorColor,
          duration: 0.15,
          ease: 'power2.out'
        });
        if (dot) {
          gsap.to(dot, {
            backgroundColor: cursorColor,
            duration: 0.15,
            ease: 'power2.out'
          });
        }
      }

      corners.forEach(corner => gsap.killTweensOf(corner, 'x,y'));
      const { cornerSize } = constants;
      const positions = [
        { x: -cornerSize * 1.5, y: -cornerSize * 1.5 },
        { x: cornerSize * 0.5, y: -cornerSize * 1.5 },
        { x: cornerSize * 0.5, y: cornerSize * 0.5 },
        { x: -cornerSize * 1.5, y: cornerSize * 0.5 }
      ];
      const tl = gsap.timeline();
      corners.forEach((corner, index) => {
        tl.to(
          corner,
          {
            x: positions[index].x,
            y: positions[index].y,
            duration: 0.3,
            ease: 'power3.out'
          },
          0
        );
      });

      resumeTimeout = setTimeout(() => {
        if (!activeTarget && cursor && spinTl) {
          const currentRotation = gsap.getProperty(cursor, 'rotation');
          const normalizedRotation = currentRotation % 360;
          spinTl.kill();
          spinTl = gsap
            .timeline({ repeat: -1 })
            .to(cursor, { rotation: '+=360', duration: spinDuration, ease: 'none' });
          gsap.to(cursor, {
            rotation: normalizedRotation + 360,
            duration: spinDuration * (1 - normalizedRotation / 360),
            ease: 'none',
            onComplete: () => {
              spinTl?.restart();
            }
          });
        }
        resumeTimeout = null;
      }, 50);

      cleanupTarget(target);
    };

    currentLeaveHandler = leaveHandler;
    target.addEventListener('mouseleave', leaveHandler);
  };

  window.addEventListener('mouseover', enterHandler, { passive: true });

  const resizeHandler = () => {
    containingBlock = getContainingBlock(cursor);
  };
  window.addEventListener('resize', resizeHandler);

  return () => {
    gsap.ticker.remove(tickerFn);
    window.removeEventListener('mousemove', moveHandler);
    window.removeEventListener('mouseover', enterHandler);
    window.removeEventListener('scroll', scrollHandler);
    window.removeEventListener('resize', resizeHandler);
    window.removeEventListener('mousedown', mouseDownHandler);
    window.removeEventListener('mouseup', mouseUpHandler);

    if (activeTarget) {
      cleanupTarget(activeTarget);
    }

    spinTl?.kill();
    document.body.style.cursor = originalCursor;

    isActive = false;
    targetCornerPositions = null;
    activeStrength.current = 0;

    if (cursor && cursor.parentNode) {
      cursor.parentNode.removeChild(cursor);
    }
  };
}

export default mountTargetCursor;
