import type { Theme } from 'vitepress'
import DefaultTheme from 'vitepress/theme'
import './style.css'

import StatCompare from './components/StatCompare.vue'
import DpsPanel from './components/DpsPanel.vue'
import UnitPage from './components/UnitPage.vue'
import UnitCard from './components/UnitCard.vue'
import UnitBrowser from './components/UnitBrowser.vue'
import BuildingCard from './components/BuildingCard.vue'
import BuildingBrowser from './components/BuildingBrowser.vue'
import BuildingPage from './components/BuildingPage.vue'
import StatsCards from './components/StatsCards.vue'
import TopDps from './components/TopDps.vue'
import DpsRanking from './components/DpsRanking.vue'
import SiteDirectory from './components/SiteDirectory.vue'

export default {
  extends: DefaultTheme,
  enhanceApp({ app }) {
    app.component('StatCompare', StatCompare)
    app.component('DpsPanel', DpsPanel)
    app.component('UnitPage', UnitPage)
    app.component('UnitCard', UnitCard)
    app.component('UnitBrowser', UnitBrowser)
    app.component('BuildingCard', BuildingCard)
    app.component('BuildingBrowser', BuildingBrowser)
    app.component('BuildingPage', BuildingPage)
    app.component('StatsCards', StatsCards)
    app.component('TopDps', TopDps)
    app.component('DpsRanking', DpsRanking)
    app.component('SiteDirectory', SiteDirectory)
  }
} satisfies Theme