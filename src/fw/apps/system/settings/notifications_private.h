/* SPDX-FileCopyrightText: 2024 Google LLC */
/* SPDX-License-Identifier: Apache-2.0 */

#pragma once

#include "applib/preferred_content_size.h"

//! The text sizes the user can choose from, on every platform
typedef enum SettingsContentSize {
  SettingsContentSize_Small,
  SettingsContentSize_Medium,
  SettingsContentSize_Large,
  SettingsContentSize_ExtraLarge,
  SettingsContentSizeCount,
} SettingsContentSize;

_Static_assert((int)SettingsContentSizeCount == (int)NumPreferredContentSizes,
               "Every preferred content size must be selectable");

//! Sizes offered on this platform, up to one step above its default
static inline int settings_content_size_count(void) {
  const int count = PreferredContentSizeDefault + 2;
  return (count < SettingsContentSizeCount) ? count : SettingsContentSizeCount;
}

static inline SettingsContentSize settings_content_size_from_preferred_size(
    PreferredContentSize preferred_size) {
  return (SettingsContentSize)preferred_size;
}

static inline PreferredContentSize settings_content_size_to_preferred_size(
    SettingsContentSize settings_size) {
  return (PreferredContentSize)settings_size;
}
