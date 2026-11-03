// Global motion: runs once on the client, before the first page initializes.
import { startIndexGraph } from './index-graph';
import { startLinks } from './links';
import { startHome } from './home';

export function setupMotion() {
  startIndexGraph();
  startLinks();
  startHome();
}
