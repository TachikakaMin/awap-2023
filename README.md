# AWAP 2023 Game AI

AWAP 2023 (I got 2nd runner-up!)

See game engine at https://github.com/ACM-CMU/awap-engine-2023-public.

Usage: put file in the bots/ folder in the repo above, and follow the directions there.


# Strategy order

See code

In general, rush to the middle of map. 

But the optimal_path() is too expensive, I have to use some very simple heuristic function rather than optimal_path(). 


# Time out

I suffer from timeout, so I add many constraints to let agent become stupid to avoid timeout. 

This agent will become random agent when there is only 70s left.

