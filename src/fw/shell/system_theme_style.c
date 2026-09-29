/* SPDX-FileCopyrightText: 2026 Core Devices LLC */
/* SPDX-License-Identifier: Apache-2.0 */

//! The system UI's style sheet: every value that changes with the user's preferred content size.
//! This file holds data only, so tests can link the real values without the rest of the theme.

#include "system_theme_style.h"

#include "applib/fonts/fonts.h"
#include "applib/graphics/gtypes.h"
#include "applib/platform.h"

#if !defined(CONFIG_RECOVERY_FW)
//! Space between a launcher glance and the display edge
#if PBL_DISPLAY_HEIGHT >= 200
#define LAUNCHER_GLANCE_INSET 10
//! Launcher text on rect displays needs only a few pixels from the right edge
#define LAUNCHER_GLANCE_RIGHT_INSET PBL_IF_RECT_ELSE(4, LAUNCHER_GLANCE_INSET)
#else
#define LAUNCHER_GLANCE_INSET       PBL_IF_RECT_ELSE(6, 23)
#define LAUNCHER_GLANCE_RIGHT_INSET LAUNCHER_GLANCE_INSET
#endif
#endif

static const SystemThemeStyle s_styles[NumPreferredContentSizes] = {
  [PreferredContentSizeSmall] =
      {
        .fonts =
            {
              [TextStyleFont_Header] = FONT_KEY_GOTHIC_14_BOLD,
#if !defined(CONFIG_RECOVERY_FW)
              [TextStyleFont_Title] = FONT_KEY_GOTHIC_18_BOLD,
              [TextStyleFont_Body] = FONT_KEY_GOTHIC_18,
#endif
              [TextStyleFont_Subtitle] = FONT_KEY_GOTHIC_18_BOLD,
              [TextStyleFont_Caption] = FONT_KEY_GOTHIC_14,
              [TextStyleFont_Footer] = FONT_KEY_GOTHIC_14,
              [TextStyleFont_MenuCellTitle] = FONT_KEY_GOTHIC_18_BOLD,
              [TextStyleFont_MenuCellSubtitle] = FONT_KEY_GOTHIC_14,
#if !defined(CONFIG_RECOVERY_FW)
              //! @note these are already the smallest fonts that exist, so they match Medium
              [TextStyleFont_TimeHeaderNumbers] = FONT_KEY_LECO_20_BOLD_NUMBERS,
#endif
              [TextStyleFont_TimeHeaderWords] = FONT_KEY_GOTHIC_14_BOLD,
              [TextStyleFont_PinSubtitle] = FONT_KEY_GOTHIC_14,
              [TextStyleFont_ParagraphHeader] = FONT_KEY_GOTHIC_14,
#if !defined(CONFIG_RECOVERY_FW)
              [TextStyleFont_CardSubtitle] =
                  PBL_IF_RECT_ELSE(FONT_KEY_GOTHIC_28_BOLD, FONT_KEY_GOTHIC_24_BOLD),
              [TextStyleFont_CalendarRecurring] =
                  PBL_IF_RECT_ELSE(FONT_KEY_GOTHIC_14, FONT_KEY_GOTHIC_14_BOLD),
              [TextStyleFont_PeekSubtitle] = FONT_KEY_GOTHIC_24,
#endif
            },
        .menu_cell =
            {
              .basic_cell_height = 40,
              .app_basic_cell_height = 44,
              .small_cell_height = 30,
              .horizontal_inset = 5,
              .title_subtitle_left_margin = 30,
              .single_line_padding_h = 10,
            },
        //! @note this is the same as Medium until Small is designed
        .option_menu =
            {
#if PBL_RECT
              .cell_heights[OptionMenuContentType_DoubleLine] = 56,
#endif
              .right_icon_spacing = PBL_IF_RECT_ELSE(7, 35),
            },
#if !defined(CONFIG_RECOVERY_FW)
        .launcher =
            {
              .title_font_key = FONT_KEY_GOTHIC_18_BOLD,
              .subtitle_font_key = FONT_KEY_GOTHIC_14,
              .glance_left_inset = LAUNCHER_GLANCE_INSET,
              .glance_right_inset = LAUNCHER_GLANCE_RIGHT_INSET,
#if PBL_RECT
              .cell_height = 42,
#else
              .focused_cell_height = 52,
              .unfocused_cell_height = 38,
#endif
            },
#endif
        .action_menu =
            {
              .unfocused_item_size = PreferredContentSizeSmall,
            },
      },
  [PreferredContentSizeMedium] =
      {
        .fonts =
            {
              [TextStyleFont_Header] = FONT_KEY_GOTHIC_18_BOLD,
#if !defined(CONFIG_RECOVERY_FW)
              [TextStyleFont_Title] = FONT_KEY_GOTHIC_24_BOLD,
              [TextStyleFont_Body] = FONT_KEY_GOTHIC_24_BOLD,
#endif
              [TextStyleFont_Subtitle] = FONT_KEY_GOTHIC_24_BOLD,
              [TextStyleFont_Caption] = FONT_KEY_GOTHIC_14,
              [TextStyleFont_Footer] = FONT_KEY_GOTHIC_18,
              [TextStyleFont_MenuCellTitle] = FONT_KEY_GOTHIC_24_BOLD,
              [TextStyleFont_MenuCellSubtitle] = FONT_KEY_GOTHIC_18,
#if !defined(CONFIG_RECOVERY_FW)
              [TextStyleFont_TimeHeaderNumbers] = FONT_KEY_LECO_20_BOLD_NUMBERS,
#endif
              [TextStyleFont_TimeHeaderWords] = FONT_KEY_GOTHIC_14_BOLD,
              [TextStyleFont_PinSubtitle] = FONT_KEY_GOTHIC_18,
              [TextStyleFont_ParagraphHeader] = FONT_KEY_GOTHIC_14,
#if !defined(CONFIG_RECOVERY_FW)
              [TextStyleFont_CardSubtitle] =
                  PBL_IF_RECT_ELSE(FONT_KEY_GOTHIC_28_BOLD, FONT_KEY_GOTHIC_24_BOLD),
              [TextStyleFont_CalendarRecurring] =
                  PBL_IF_RECT_ELSE(FONT_KEY_GOTHIC_14, FONT_KEY_GOTHIC_14_BOLD),
              [TextStyleFont_PeekSubtitle] = FONT_KEY_GOTHIC_24,
#endif
            },
        .menu_cell =
            {
              .basic_cell_height = 44,
              .app_basic_cell_height = 44,
              .small_cell_height = 34,
              .horizontal_inset = 5,
              .title_subtitle_left_margin = 30,
              .single_line_padding_h = 10,
            },
        .option_menu =
            {
#if PBL_RECT
              .cell_heights[OptionMenuContentType_DoubleLine] = 56,
#endif
              .right_icon_spacing = PBL_IF_RECT_ELSE(7, 35),
            },
#if !defined(CONFIG_RECOVERY_FW)
        .launcher =
            {
              .title_font_key = PBL_IF_RECT_ELSE(FONT_KEY_GOTHIC_24_BOLD, FONT_KEY_GOTHIC_18_BOLD),
              .subtitle_font_key = PBL_IF_RECT_ELSE(FONT_KEY_GOTHIC_18, FONT_KEY_GOTHIC_14),
              .glance_left_inset = LAUNCHER_GLANCE_INSET,
              .glance_right_inset = LAUNCHER_GLANCE_RIGHT_INSET,
              .title_margin_h = PBL_IF_RECT_ELSE(-3, 0),
#if PBL_RECT
              .cell_height = 50,
              .title_only_cell_height = 42,
#else
              .focused_cell_height = 52,
              .unfocused_cell_height = 38,
#endif
            },
#endif
        .action_menu =
            {
              .unfocused_item_size = PreferredContentSizeMedium,
            },
      },
  [PreferredContentSizeLarge] =
      {
        .fonts =
            {
              [TextStyleFont_Header] = FONT_KEY_GOTHIC_28_BOLD,
#if !defined(CONFIG_RECOVERY_FW)
              [TextStyleFont_Title] = FONT_KEY_GOTHIC_28_BOLD,
              [TextStyleFont_Body] = FONT_KEY_GOTHIC_28,
#endif
              [TextStyleFont_Subtitle] = FONT_KEY_GOTHIC_28,
              [TextStyleFont_Caption] = FONT_KEY_GOTHIC_24,
              [TextStyleFont_Footer] = FONT_KEY_GOTHIC_24,
              [TextStyleFont_MenuCellTitle] = FONT_KEY_GOTHIC_28_BOLD,
              [TextStyleFont_MenuCellSubtitle] = FONT_KEY_GOTHIC_24,
#if !defined(CONFIG_RECOVERY_FW)
              [TextStyleFont_TimeHeaderNumbers] = FONT_KEY_LECO_26_BOLD_NUMBERS_AM_PM,
#endif
              [TextStyleFont_TimeHeaderWords] = FONT_KEY_GOTHIC_24_BOLD,
              [TextStyleFont_PinSubtitle] = FONT_KEY_GOTHIC_28,
              [TextStyleFont_ParagraphHeader] = FONT_KEY_GOTHIC_24_BOLD,
#if !defined(CONFIG_RECOVERY_FW)
              [TextStyleFont_CardSubtitle] =
                  PBL_IF_RECT_ELSE(FONT_KEY_GOTHIC_28_BOLD, FONT_KEY_GOTHIC_24_BOLD),
              [TextStyleFont_CalendarRecurring] = FONT_KEY_GOTHIC_24_BOLD,
              [TextStyleFont_PeekSubtitle] = FONT_KEY_GOTHIC_24,
#endif
            },
        .menu_cell =
            {
              .basic_cell_height = 61,
              .app_basic_cell_height = 61,
              .small_cell_height = 42,
              .horizontal_inset = 10,
              .title_subtitle_left_margin = 34,
              .single_line_padding_h = 10,
            },
        .option_menu =
            {
#if PBL_RECT
              .cell_heights[OptionMenuContentType_SingleLine] = 46,
#endif
              .top_inset = 1,
              .right_icon_spacing = PBL_IF_RECT_ELSE(10, 35),
              .text_inset_single = -1,
              .text_inset_multi = -3,
              .right_text_inset_with_icon = 4,
            },
#if !defined(CONFIG_RECOVERY_FW)
        .launcher =
            {
              .title_font_key = PBL_IF_RECT_ELSE(FONT_KEY_GOTHIC_28_BOLD, FONT_KEY_GOTHIC_24_BOLD),
              .subtitle_font_key = PBL_IF_RECT_ELSE(FONT_KEY_GOTHIC_24, FONT_KEY_GOTHIC_18),
              .glance_left_inset = LAUNCHER_GLANCE_INSET,
              .glance_right_inset = LAUNCHER_GLANCE_RIGHT_INSET,
              .title_margin_h = PBL_IF_RECT_ELSE(-3, 0),
#if PBL_RECT
              .cell_height = 60,
              .title_only_cell_height = 46,
#else
              .focused_cell_height = 55,
              .unfocused_cell_height = 45,
#endif
            },
#endif
        .action_menu =
            {
              .unfocused_item_size = PreferredContentSizeLarge,
            },
      },
  [PreferredContentSizeExtraLarge] = {
    .fonts =
        {
#if !defined(CONFIG_RECOVERY_FW)
          [TextStyleFont_Header] = FONT_KEY_GOTHIC_36_BOLD,
          [TextStyleFont_Title] = FONT_KEY_GOTHIC_36_BOLD,
          [TextStyleFont_Body] = FONT_KEY_GOTHIC_36,
          [TextStyleFont_Subtitle] = FONT_KEY_GOTHIC_36,
#else
          [TextStyleFont_Header] = FONT_KEY_GOTHIC_28_BOLD,
          [TextStyleFont_Subtitle] = FONT_KEY_GOTHIC_28,
#endif
          [TextStyleFont_Caption] = FONT_KEY_GOTHIC_28,
          [TextStyleFont_Footer] = FONT_KEY_GOTHIC_28,
#if !defined(CONFIG_RECOVERY_FW)
          [TextStyleFont_MenuCellTitle] =
              PBL_IF_RECT_ELSE(FONT_KEY_GOTHIC_36_BOLD, FONT_KEY_GOTHIC_28_BOLD),
          [TextStyleFont_MenuCellSubtitle] = FONT_KEY_GOTHIC_28,
#else
          [TextStyleFont_MenuCellTitle] = FONT_KEY_GOTHIC_28_BOLD,
          [TextStyleFont_MenuCellSubtitle] = FONT_KEY_GOTHIC_28,
#endif
#if !defined(CONFIG_RECOVERY_FW)
          //! Only digits and separators; AM/PM is drawn with TimeHeaderWords
          [TextStyleFont_TimeHeaderNumbers] = FONT_KEY_LECO_32_BOLD_NUMBERS,
#endif
          [TextStyleFont_TimeHeaderWords] = FONT_KEY_GOTHIC_28_BOLD,
#if !defined(CONFIG_RECOVERY_FW)
          [TextStyleFont_PinSubtitle] = FONT_KEY_GOTHIC_36,
#else
          [TextStyleFont_PinSubtitle] = FONT_KEY_GOTHIC_28,
#endif
          [TextStyleFont_ParagraphHeader] = FONT_KEY_GOTHIC_28_BOLD,
#if !defined(CONFIG_RECOVERY_FW)
          [TextStyleFont_CardSubtitle] =
              PBL_IF_RECT_ELSE(FONT_KEY_GOTHIC_28_BOLD, FONT_KEY_GOTHIC_24_BOLD),
          [TextStyleFont_CalendarRecurring] = FONT_KEY_GOTHIC_24_BOLD,
          [TextStyleFont_PeekSubtitle] = FONT_KEY_GOTHIC_24,
#endif
        },
    .menu_cell =
        {
          .basic_cell_height = 78,
          .app_basic_cell_height = 85,
          .small_cell_height = 52,
          .horizontal_inset = 10,
          .title_subtitle_left_margin = 34,
          .single_line_padding_h = 10,
        },
    .option_menu =
        {
#if PBL_RECT
          .cell_heights[OptionMenuContentType_SingleLine] = 56,
#endif
          .top_inset = 1,
          .right_icon_spacing = PBL_IF_RECT_ELSE(10, 35),
          .text_inset_single = -1,
          .text_inset_multi = -3,
          .right_text_inset_with_icon = 4,
        },
#if !defined(CONFIG_RECOVERY_FW)
    .launcher =
        {
          .title_font_key = PBL_IF_RECT_ELSE(FONT_KEY_GOTHIC_36_BOLD, FONT_KEY_GOTHIC_28_BOLD),
          .subtitle_font_key = PBL_IF_RECT_ELSE(FONT_KEY_GOTHIC_28, FONT_KEY_GOTHIC_24),
          .glance_left_inset = LAUNCHER_GLANCE_INSET,
          .glance_right_inset = LAUNCHER_GLANCE_RIGHT_INSET,
          .title_margin_h = PBL_IF_RECT_ELSE(-3, 0),
#if PBL_RECT
          .cell_height = 76,
          .title_only_cell_height = 56,
#else
          .focused_cell_height = 66,
          .unfocused_cell_height = 56,
#endif
        },
#endif
    .action_menu = {
      .unfocused_item_size = PreferredContentSizeLarge,
    },
  },
};

const SystemThemeStyle *system_theme_get_style_for_size(PreferredContentSize size) {
  return &s_styles[(size < NumPreferredContentSizes) ? size : PreferredContentSizeDefault];
}

const SystemThemeStyle *system_theme_get_style(void) {
  return system_theme_get_style_for_size(system_theme_get_content_size());
}
