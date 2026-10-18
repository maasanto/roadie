import assert from "node:assert/strict";
import { test } from "node:test";

// gig.js reads the page boot (window.lang, window.translations) and the global __ at import time.
globalThis.window = globalThis;
window.lang = "fr";
const {
	columnTotals,
	feeLabelOf,
	formatDate,
	formatFee,
	gigControls,
	gigTitleFromPicks,
	memberOptions,
	titleAfterPick,
	totalFee,
} = await import("./gig.js");

test("a gig is named after its edition, else its festival, else its venue", () => {
	const controls = gigControls({
		festivals: [{ name: "acme", title: "Acme Open Air" }],
		editions: [{ name: "acme-2027", title: "Acme Open Air 2027", festival: "acme" }],
		venues: [{ name: "hall", title: "Acme Hall" }],
	});
	const titleOf = (form) =>
		gigTitleFromPicks({ festival: "", festival_edition: "", venue: "", ...form }, controls);

	assert.equal(titleOf({ venue: "hall" }), "Acme Hall");
	assert.equal(titleOf({ festival: "acme", venue: "hall" }), "Acme Open Air");
	assert.equal(
		titleOf({ festival: "acme", festival_edition: "acme-2027", venue: "hall" }),
		"Acme Open Air 2027"
	);
	assert.equal(titleOf({}), "");
	assert.equal(titleOf({ festival: "not-loaded-yet", venue: "hall" }), "Acme Hall");
});

test("a blank title takes the pick's name, and keeps following picks until the member types their own", () => {
	assert.equal(titleAfterPick("", "", "Acme Hall"), "Acme Hall");
	assert.equal(titleAfterPick("Acme Hall", "Acme Hall", "Acme Open Air 2027"), "Acme Open Air 2027");
	assert.equal(
		titleAfterPick("Acme Hall residency", "Acme Hall", "Acme Open Air 2027"),
		"Acme Hall residency"
	);
	assert.equal(titleAfterPick("Release party", "", "Acme Hall"), "Release party");
});

test("a date in the current year is shown without its year", () => {
	const thisYear = new Date().getFullYear();
	assert.equal(formatDate(`${thisYear}-10-12`), "12 oct.");
});

test("a date in another year keeps its year, so next summer's festival is not mistaken for this one", () => {
	const nextYear = new Date().getFullYear() + 1;
	assert.equal(formatDate(`${nextYear}-07-14`), `14 juil. ${nextYear}`);
});

// French groups digits and sets the symbol apart with no-break spaces.
const withPlainSpaces = (text) => text.replace(/[\u202f\u00a0]/gu, " ");

test("a fee reads in the site's currency, cents only when it has some", (context) => {
	context.after(() => delete window.currency);
	window.currency = "EUR";
	assert.equal(withPlainSpaces(formatFee(1500)), "1 500 €");
	assert.equal(withPlainSpaces(formatFee(1500.5)), "1 500,50 €");
});

test("a site without a default currency still groups the fee's digits", () => {
	assert.equal(withPlainSpaces(formatFee(1500)), "1 500");
});

test("a currency Intl does not know shows the plain amount instead of breaking the board", (context) => {
	context.after(() => delete window.currency);
	window.currency = "Beer tokens";
	assert.equal(withPlainSpaces(formatFee(1500.505)), "1 500,51");
});

test("the fee takes the band's label, and leaves the board once the customiser hides it", () => {
	assert.equal(feeLabelOf([{ fieldname: "fee", label: "Net fee" }]), "Net fee");
	assert.equal(feeLabelOf([{ fieldname: "fee", label: "Net fee", hidden: 1 }]), null);
	assert.equal(feeLabelOf([{ fieldname: "title", label: "Title" }]), null);
});

test("a column totals the fees it has and counts an unpriced gig as nothing", () => {
	assert.equal(totalFee([{ fee: 1500 }, { fee: 0 }, {}, { fee: 700.5 }]), 2200.5);
	assert.equal(totalFee([]), 0);
});

test("past the row limit a column counts every matching gig, not only the cards the board loaded", () => {
	const loadedCards = [{ status: "Contacted", fee: 2600 }];
	const statusTotals = [
		{ status: "Contacted", count: 5, fee: 13000 },
		{ status: "Declined", count: 2, fee: 1000 },
		{ status: "Dropped", count: 1 },
	];
	assert.deepEqual(columnTotals(["Contacted"], loadedCards, null), { count: 1, fee: 2600 });
	assert.deepEqual(columnTotals(["Contacted"], loadedCards, statusTotals), { count: 5, fee: 13000 });
	assert.deepEqual(columnTotals(["Declined", "Dropped"], [], statusTotals), { count: 3, fee: 1000 });
});

test("members are offered by full name and valued by their user", () => {
	assert.deepEqual(memberOptions([{ name: "jane@example.com", full_name: "Jane Doe" }]), [
		{ label: "Jane Doe", value: "jane@example.com" },
	]);
});

test("an absent member list yields no options", () => {
	assert.deepEqual(memberOptions(undefined), []);
});
