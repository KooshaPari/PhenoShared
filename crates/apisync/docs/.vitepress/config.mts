import { defineConfig } from "vitepress";

export default defineConfig({
	title: "Apisync",
	description:
		"Universal API toolkit with REST, GraphQL, and WebSocket support",
	base: "/apisync/",
	themeConfig: {
		nav: [
			{ text: "Home", link: "/" },
			{ text: "API", link: "/api" },
			{ text: "Specs", link: "/traceability/" },
		],
		sidebar: [
			{
				text: "Guide",
				items: [
					{ text: "Overview", link: "/" },
					{ text: "Installation", link: "/installation" },
					{ text: "Quick Start", link: "/quickstart" },
				],
			},
			{
				text: "Reference",
				items: [
					{ text: "API Reference", link: "/api" },
					{ text: "Architecture", link: "/architecture" },
				],
			},
			{
				text: "Specs & Governance",
				items: [
					{ text: "Traceability", link: "/traceability/" },
					{ text: "User Journeys", link: "/journeys/" },
					{ text: "User Stories", link: "/stories/" },
					{ text: "ADRs", link: "/adr/" },
					{ text: "SOTA Research", link: "/research/SOTA" },
				],
			},
		],
	},
});
