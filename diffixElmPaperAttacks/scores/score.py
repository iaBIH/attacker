
class score:
    def __init__(self,statGuess):
        self.statGuess = statGuess
        if statGuess < 0 or statGuess > 1.0:
            print(f"Bad statGuess {statGuess}")
            quit()
        # An attack attempt
        self.attempts = 0
        # A claim that victim has attribute
        self.claimHas = 0
        # Total claims (both has and doesn't have attribute)
        self.totalClaims = 0
        # Times a claim that the victim has attribute is correct
        self.claimCorrect = 0

    def attempt(self,makesClaim,claimHas,claimCorrect):
        # This is an attempt
        self.attempts += 1
        if makesClaim:
            self.totalClaims += 1
        else:
            # Not making a claim
            return
        if claimHas:
            self.claimHas += 1
        else:
            # Making a claim, but claim is negative, so don't care if correct
            return
        if claimCorrect:
            self.claimCorrect += 1

    def computeScore(self):
        self.claimRate = self.totalClaims / self.attempts
        if self.claimHas == 0:
            self.confidence = 0
        else:
            self.confidence = self.claimCorrect / self.claimHas

        if self.statGuess == 1.0:
            # really this should never happen (statistical guess always right)
            if self.confidence == 1.0:
                return self.claimRate,1.0
            else:
                return self.claimRate,-1.0
        self.confImprove = (self.confidence-self.statGuess)/(1.0-self.statGuess)
        return self.claimRate, self.confImprove, self.confidence

    def prettyScore(self):
        cr = str(f"{self.claimRate:.2}")
        ci = str(f"{self.confImprove:.2}")
        c = str(f"{self.confidence:.2}")
        return cr,ci,c