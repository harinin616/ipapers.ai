from kokoro import KPipeline
import soundfile as sf
pipeline = KPipeline(lang_code='a')

texts = [
    """
It all began on 1 July, when an asteroid-hunting telescope in Chile spotted a tiny white dot hurtling against the background stars. The online chatter began almost immediately as astronomers tracked the object in earlier images and amateur observations. Soon it was clear the dot was moving through the Solar System so fast—209,000 kilometers per hour—that it could not be orbiting the Sun. That night, says Michigan State University (MSU) astronomer Darryl Seligman, “I woke up at 1 a.m. [and] saw messages saying, ‘Oh, this is for sure interstellar.’” The next day, he and his colleagues began typing up the first paper characterizing the new intruder.

3l/ATLAS, named for the instrument that found it, the Asteroid Terrestrial-impact Last Alert System (ATLAS) survey telescope, is just the third object of its kind ever spotted. Like its predecessors, 1I/‘Oumuamua in 2017 and 2I/Borisov in 2019, it is a stray leftover from the formation of exoplanets around other stars and will vanish back into interstellar space within months. As a result, astronomers around the world are swiveling ground- and space-based telescopes toward the object, hoping to catch it while it remains visible, and trying to make sense of early clues. “I couldn’t really work on Thursday,” says University of Cologne astronomer Susanne Pfalzner, a theoretician specializing in stellar and planetary formation. “I was just jumping about.”

Beyond a few basics, ATLAS remains mostly a mystery, but astronomers have already learned enough to intrigue them. For one, the object is conspicuously bright. ATLAS was discovered while it was still 670 million kilometers from the Sun, out near the orbit of Jupiter—more than five times farther than ‘Oumuamua was when it was first spotted. This suggests ATLAS might be as large as 20 kilometers across, much larger than ‘Oumuamua (thought to be a cigar-shaped chunk 400 meters long) and Borisov (975 meters wide). However, estimates of the object’s size come with an asterisk. If ATLAS is outgassing like a comet, it might be surrounded by a haze that makes it appear larger than it really is.
    """
]

def generate_audio(texts, titles, output_dir="./"):
    generator = pipeline(texts, voice='af_heart')
    for i, ((gs, ps, audio), title) in enumerate(zip(generator, titles)):
        print(i, gs, ps)
        sf.write(f'{output_dir}/{title}.wav', audio, 24000)

generate_audio(texts, ["titles"])