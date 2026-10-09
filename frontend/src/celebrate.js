// The logo's orange, plus Espresso green and blue.
const CONFETTI_COLOURS = ["#d35a08", "var(--surface-green-3)", "var(--surface-blue-2)"];
const PIECES = 18;
const DURATION_MS = 900;

export function burstConfetti(origin) {
	if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
	const { left, top, width } = origin.getBoundingClientRect();
	for (let index = 0; index < PIECES; index++) {
		const piece = document.createElement("span");
		Object.assign(piece.style, {
			position: "fixed",
			left: `${left + width / 2}px`,
			top: `${top + 12}px`,
			width: "7px",
			height: "10px",
			borderRadius: "2px",
			background: CONFETTI_COLOURS[index % CONFETTI_COLOURS.length],
			pointerEvents: "none",
			zIndex: 50,
		});
		document.body.append(piece);

		const angle = Math.PI * (1.15 + (0.7 * index) / (PIECES - 1));
		const distance = 60 + Math.random() * 70;
		const peakX = Math.cos(angle) * distance;
		const peakY = Math.sin(angle) * distance;
		const spin = 180 + Math.random() * 360;
		piece
			.animate(
				[
					{ transform: "translate(0, 0) rotate(0deg)", opacity: 1 },
					{ transform: `translate(${peakX}px, ${peakY}px) rotate(${spin / 2}deg)`, opacity: 1, offset: 0.55 },
					{ transform: `translate(${peakX * 1.2}px, ${peakY + 70}px) rotate(${spin}deg)`, opacity: 0 },
				],
				{ duration: DURATION_MS, easing: "cubic-bezier(.2, .7, .4, 1)" },
			)
			.finished.then(() => piece.remove());
	}
}
