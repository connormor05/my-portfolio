async function runSafetyCheck(question) {
  try {
    // Ignore empty or whitespace-only messages
    if (!question || question.trim() === "") {
      return {
        allowed: true,
        category: "clean",
        reason: "Empty message ignored"
      };
    }

    const lower = question.toLowerCase();


    // Category lists
    const categories = {
      sexual_content: [
        "sex", "porn", "nude", "naked", "xxx", "horny", "explicit",
        "blowjob", "anal", "cum", "fetish", "erotic"
      ],

      violence: [
        "kill", "killing", "killed", "murder", "stab", "shoot", "gun",
        "attack", "assault", "beat", "bomb", "explode", "execution"
      ],

      self_harm: [
        "suicide", "kill myself", "end my life", "hurt myself",
        "self harm", "cut myself", "i want to die", "i want to end it",
        "shoot myself", "overdose"
      ],

      hate_speech: [
        "bitch", "slur", "racist", "bigot", "hate", "disgusting people",
        "go back to your country"
      ]
    };


    // Check each category
    for (const [category, words] of Object.entries(categories)) {
      if (words.some(w => lower.includes(w))) {
        return {
          allowed: false,
          category,
          reason: `Message flagged for ${category.replace("_", " ")}`
        };
      }
    }

    // If nothing matched
    return {
      allowed: true,
      category: "clean",
      reason: "No safety issues detected"
    };

  } catch (error) {
    console.error("Safety check failed:", error);
    return {
      allowed: false,
      category: "error",
      reason: "Safety system error"
    };
  }
}

module.exports = { runSafetyCheck };

