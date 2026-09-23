RESPONSES={
"plastic":"Clean plastic containers, separate food residue, and place accepted plastics in your recyclable stream.",
"e-waste":"Keep electronics out of normal bins. Use an authorized e-waste collection or recycling center.",
"wet":"Wet or organic waste can usually go to a composting or organic-waste stream where available.",
"dry":"Keep dry recyclables clean and dry, then separate paper, plastic, glass and metal according to local rules.",
"recycle":"Check the item label and your local recycler's accepted materials. When unsure, use a specialized collection point.",
"reduce":"Prefer reusable products, avoid unnecessary packaging, repair items, and buy only what you need."}
def reply(message):
    m=message.lower()
    for key,answer in RESPONSES.items():
        if key in m:return answer
    return "I can help with plastic, e-waste, wet/dry separation, recycling, reuse, and waste reduction. Try one of those topics."
