Fast, Table-Tiling Python Window Manager (FTTPWM)
=======================================================

Ideas
-----

- Use xpyb and xpybutil
- Support both "static" and "dynamic" layouts, with these settings:
  * `onNewWindow` - one of: (for all but `tab`, see also the `newContainerDirectionH` and `newContainerDirectionV` settings)
    + `newRow` - create a new screen-width row containing the new window
    + `newCol` - create a new screen-height column containing the new window
    + `splitH` - split the current container horizontally, resulting in the container's contents and the new window each taking up half the space
    + `splitV` - split the current container vertically, resulting in the container's contents and the new window each taking up half the space
    + `tab` - open the new window as a new tab in the current container (don't change the container layout at all)
  * `onEmptyContainer` - one of:
    + `keep` - leave emptied containers alone (don't change the container layout at all)
    + `collapseH` - close emptied containers, and distribute the vacated space among adjacent containers, preferring ones to the left and right of the space
    + `collapseV` - close emptied containers, and distribute the vacated space among adjacent containers, preferring ones above and below the space
  * `newContainerPolicy` - one of:
    + `fair` - the new container takes 1/(n+1) of the screen (where 'n' is the number of columns currently on the screen), shrinking all other containers equally to compensate
    + `nearby` - the new container takes 1/2 of the space initially occupied by the nearest container in the `newContainerDirection` direction, shrinking that container to compensate
  * `newContainerDirectionH` - one of:
    + `left`
    + `right`
  * `newContainerDirectionV` - one of:
    + `above`
    + `below`
