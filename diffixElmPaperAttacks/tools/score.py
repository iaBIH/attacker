
class score:
    def __init__(self,statGuess=None):
        # statGuess here is for the case where it is always the same
        self.statGuess = statGuess
        if statGuess and (statGuess < 0 or statGuess > 1.0):
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
        # To keep track of average statGuess
        self.totalStatGuess = 0

    def attempt(self,makesClaim,claimHas,claimCorrect,statGuess=None):
        # This is an attempt
        self.attempts += 1
        if makesClaim:
            self.totalClaims += 1
            # This statGuess is for this specific claim
            if statGuess is not None:
                self.totalStatGuess += statGuess
            else:
                self.totalStatGuess += self.statGuess
        else:
            # Not making a claim
            return
        if claimHas:
            # claim is positive (victim has attributes)
            self.claimHas += 1
        else:
            # Making a claim, but claim is negative, so don't care if correct
            return
        if claimCorrect:
            self.claimCorrect += 1

    def computeScore(self):
        self.confImprove = 0.0
        self.confidence = 0.0
        if self.attempts == 0:
            return 0,0,0
        self.claimRate = self.totalClaims / self.attempts
        if self.totalClaims == 0:
            return 0,0,0
        if self.claimHas == 0:
            self.confidence = 0.0
        else:
            self.confidence = self.claimCorrect / self.claimHas

        avStatGuess = self.totalStatGuess / self.totalClaims
        if avStatGuess == 1.0:
            # really this should almost never happen (statistical guess always right)
            if self.confidence == 1.0:
                return self.claimRate,1.0,1.0
            else:
                return self.claimRate,-1.0,0.0
        self.confImprove = (self.confidence-avStatGuess)/(1.0-avStatGuess)
        return self.claimRate, self.confImprove, self.confidence

    def prettyScore(self):
        cr = str(f"{self.claimRate:.2}")
        ci = str(f"{self.confImprove:.2}")
        c = str(f"{self.confidence:.2}")
        return cr,ci,c