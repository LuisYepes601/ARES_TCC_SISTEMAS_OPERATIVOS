"""ui/styles/performance_palette.py"""
from dataclasses import dataclass
from ui.styles.theme import THEME_DARK, THEME_LIGHT

COLOR_CPU  = "#5c7cfa"
COLOR_MEM  = "#38bdf8"
COLOR_DISK = "#4ade80"
COLOR_WIFI = "#e879f9"
COLOR_GPU  = "#fb923c"


@dataclass(frozen=True)
class PerformancePalette:
    bg:            str
    bg_elevated:   str
    bg_card:       str
    text_primary:  str
    text_secondary: str
    card_border:   str
    grid_alpha:    float
    fill_cpu:      str
    fill_mem:      str
    fill_disk:     str
    fill_wifi:     str
    fill_gpu:      str


PALETTE_DARK = PerformancePalette(
    bg="#08080f",
    bg_elevated="#06060d",
    bg_card="#06060d",
    text_primary="#c8c8e0",
    text_secondary="#30304e",
    card_border="#111120",
    grid_alpha=0.05,
    fill_cpu="#5c7cfa22",
    fill_mem="#38bdf822",
    fill_disk="#4ade8022",
    fill_wifi="#e879f922",
    fill_gpu="#fb923c22",
)

PALETTE_LIGHT = PerformancePalette(
    bg="#f0f0f8",
    bg_elevated="#ffffff",
    bg_card="#f8f8ff",
    text_primary="#1a1a2e",
    text_secondary="#6666aa",
    card_border="rgba(80,80,180,0.12)",
    grid_alpha=0.12,
    fill_cpu="#5c7cfa33",
    fill_mem="#38bdf833",
    fill_disk="#4ade8033",
    fill_wifi="#e879f933",
    fill_gpu="#fb923c33",
)


def palette_for_theme(theme: str) -> PerformancePalette:
    return PALETTE_LIGHT if theme == THEME_LIGHT else PALETTE_DARK
