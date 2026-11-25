/**
 * AgilePlus Desktop — Electrobun main process (step-1, offline-first).
 */

import { BrowserWindow } from "electrobun/bun";
import { RepoBridge } from "./repo-bridge";
import { CLI } from "./cli";
import { AppPaths } from "./paths";
import { createRepoRpc } from "./views";

const paths = AppPaths.fromCwd(process.cwd());
const repo = new RepoBridge(paths);
const cli = new CLI(paths);
const rpc = createRepoRpc({ repo, cli, paths });

new BrowserWindow({
  title: "AgilePlus",
  url: "views://main/index.html",
  rpc,
  frame: {
    x: 100,
    y: 100,
    width: 1180,
    height: 760,
  },
});
