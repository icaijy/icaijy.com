"""Study-design scoped, original numerical and reasoning question families.

The families below vary the mathematical or scientific work itself.  They are
not cosmetic rewrites: every generated item has different givens and a freshly
computed answer.  This keeps the one-minute format broad without pretending a
generic sentence prefix is a new question.
"""
from math import comb


def item(topic, prompt, correct, wrong, note):
    return (topic, prompt, str(correct), [str(value) for value in wrong], note)


def chemistry_u12():
    records = []
    molar = [('NaCl', 58.5), ('CO_2', 44.0), ('O_2', 32.0), ('CaCO_3', 100.1), ('NH_3', 17.0), ('CH_4', 16.0)]
    for formula, mass in molar:
        moles = 0.25
        sample = mass * moles
        records.append(item('U1 · Quantitative chemistry', rf'A sample contains {sample:g} g of \(\mathrm{{{formula}}}\). Its amount is', '0.250 mol', ['0.125 mol', '0.500 mol', f'{sample:g} mol'], rf'\(n=m/M={sample:g}/{mass:g}=0.250\).'))
    for volume, concentration in ((0.250, 0.40), (0.500, 0.12), (0.100, 1.50), (0.0250, 0.80), (0.200, 0.35), (0.0500, 2.00)):
        amount = volume * concentration
        records.append(item('U2 · Solution stoichiometry', f'A solution has volume {volume:.3f} L and concentration {concentration:.2f} M. The amount of solute is', f'{amount:.3f} mol', [f'{amount * 10:.3f} mol', f'{amount / 10:.4f} mol', f'{volume / concentration:.3f} mol'], rf'\(n=cV={concentration:.2f}\times{volume:.3f}={amount:.3f}\).'))
    for initial, final, c1 in ((20, 100, 0.50), (25, 250, 0.80), (10, 200, 1.20), (40, 200, 0.25), (5, 50, 2.00)):
        c2 = c1 * initial / final
        records.append(item('U2 · Dilution', f'{initial} mL of {c1:.2f} M solution is diluted to {final} mL. The new concentration is', f'{c2:.3f} M', [f'{c1 * final / initial:.2f} M', f'{c1:.2f} M', f'{c2 / 10:.4f} M'], rf'Use \(c_1V_1=c_2V_2\), giving \(c_2={c2:.3f}\).'))
    for volume in (2.48, 4.96, 12.4, 24.8, 49.6):
        n = volume / 24.8
        records.append(item('U2 · Gases', f'At SLC, {volume:g} L of an ideal gas is approximately', f'{n:g} mol', [f'{n * 2:g} mol', f'{n * 10:g} mol', f'{n + 0.25:g} mol'], rf'At SLC, \(n=V/24.8={n:g}\).'))
    oxidation = [('SO_4^{2-}', 'S', '+6'), ('NO_3^-', 'N', '+5'), ('MnO_4^-', 'Mn', '+7'), ('H_2O_2', 'O', '−1'), ('NH_4^+', 'N', '−3')]
    for species, atom, answer in oxidation:
        records.append(item('U2 · Redox', rf'The oxidation number of {atom} in \(\mathrm{{{species}}}\) is', answer, ['0', '+2', '−2'], 'Oxidation numbers sum to the overall charge.'))
    isotope_cases = [(24, 25, 79.0, 24.21), (35, 37, 75.0, 35.50), (10, 11, 20.0, 10.80), (63, 65, 69.0, 63.62)]
    for low, high, low_pct, mean in isotope_cases:
        records.append(item('U1 · Isotopes', f'An element is {low_pct:g}% isotope-{low} and {100-low_pct:g}% isotope-{high}. Its relative atomic mass is', f'{mean:.2f}', [f'{(low+high)/2:.2f}', f'{low_pct/100:.2f}', f'{high-low:.2f}'], 'Use the abundance-weighted mean of isotope masses.'))
    for solute, solvent, rf in ((3.2, 8.0, 0.40), (4.5, 6.0, 0.75), (1.8, 9.0, 0.20), (5.4, 7.2, 0.75)):
        records.append(item('U1 · Chromatography', f'A spot travels {solute:g} cm and the solvent front {solvent:g} cm. The retention factor is', f'{rf:.2f}', [f'{1/rf:.2f}', f'{solute+solvent:.1f}', f'{solvent-solute:.1f}'], rf'\(R_f={solute:g}/{solvent:g}={rf:.2f}\).'))
    records.extend([
        item('U1 · Materials', 'A polymer that can be softened and reshaped repeatedly is best described as', 'thermoplastic', ['thermosetting', 'covalent network', 'ceramic'], 'Thermoplastic chains can move past one another when heated.'),
        item('U1 · Organic chemistry', r'Which molecular formula fits a saturated acyclic alkane with six carbon atoms?', r'\(\mathrm{C_6H_{14}}\)', [r'\(\mathrm{C_6H_{12}}\)', r'\(\mathrm{C_6H_{10}}\)', r'\(\mathrm{C_6H_6}\)'], r'Alkanes follow \(\mathrm{C_nH_{2n+2}}\).'),
        item('U2 · Water analysis', 'A blank sample in colorimetry is used primarily to', 'correct for absorbance from solvent and apparatus', ['set the unknown concentration', 'increase analyte concentration', 'identify every ion'], 'The blank establishes the background response.'),
        item('U2 · Titration', 'Rinsing a burette with distilled water immediately before filling it with titrant would usually', 'dilute the titrant remaining in the burette', ['increase its stated concentration', 'change the analyte amount', 'make the endpoint exact'], 'Residual water lowers the delivered titrant concentration.'),
    ])
    return records


def chemistry_u34():
    records = []
    cells = [(0.80, -0.76), (0.34, -0.44), (1.36, 0.54), (0.77, -0.14), (0.15, -0.28), (1.23, 0.40)]
    for cathode, anode in cells:
        voltage = cathode - anode
        records.append(item('U3 · Electrochemical cells', f'A galvanic cell has listed reduction potentials {cathode:+.2f} V at the cathode and {anode:+.2f} V at the anode. Its standard cell potential is', f'{voltage:.2f} V', [f'{cathode+anode:.2f} V', f'{abs(anode):.2f} V', f'{voltage/2:.2f} V'], r'\(E^\circ_{cell}=E^\circ_{cathode}-E^\circ_{anode}\).'))
    for current, seconds in ((1.5, 40), (2.0, 90), (0.50, 240), (3.0, 50), (4.0, 75), (0.25, 400)):
        charge = current * seconds
        records.append(item('U3 · Electrolysis', f'A current of {current:g} A flows for {seconds} s. The charge transferred is', f'{charge:g} C', [f'{seconds/current:g} C', f'{charge/1000:g} C', f'{current+seconds:g} C'], rf'\(Q=It={current:g}\times{seconds}={charge:g}\ \mathrm C\).'))
    for factor, rise in ((2.5, 4.0), (1.2, 6.0), (0.80, 5.0), (3.0, 2.5), (4.5, 3.0)):
        energy = factor * rise
        records.append(item('U3 · Calorimetry', f'A calorimeter factor is {factor:g} kJ °C⁻¹ and temperature rises {rise:g} °C. Energy absorbed is', f'{energy:g} kJ', [f'{factor/rise:g} kJ', f'{factor*2:g} kJ', f'{energy*1000:g} kJ'], rf'\(E=CF\Delta T={energy:g}\ \mathrm{{kJ}}\).'))
    for q, k, direction in ((0.20, 2.0, 'towards products'), (5.0, 0.50, 'towards reactants'), (1.0, 1.0, 'at equilibrium'), (0.040, 0.80, 'towards products'), (12.0, 3.0, 'towards reactants')):
        wrong = [x for x in ('towards products', 'towards reactants', 'at equilibrium', 'until all reactant is consumed') if x != direction]
        records.append(item('U3 · Equilibrium', rf'For a reaction mixture, \(Q={q:g}\) and \(K={k:g}\). The net change is', direction, wrong[:3], 'Compare Q with K: the system changes until Q equals K.'))
    records.extend([
        item('U3 · Equilibrium', 'Compressing a gaseous equilibrium shifts it toward the side with', 'fewer moles of gas', ['more moles of gas', 'more solid', 'the catalyst'], 'The shift opposes the pressure increase.'),
        item('U3 · Equilibrium', 'Adding a catalyst to an equilibrium mixture changes', 'the time taken to re-establish equilibrium, not the equilibrium composition', ['the equilibrium constant', 'the reaction enthalpy', 'only the forward rate'], 'Both directions are accelerated without changing K.'),
        item('U3 · Fuels', 'A life-cycle assessment of a fuel should include', 'impacts from feedstock extraction through use and disposal', ['combustion energy only', 'purchase price only', 'tailpipe carbon dioxide only'], 'Life-cycle analysis considers all major stages.'),
        item('U3 · Energy efficiency', 'A process releases 240 kJ from fuel and delivers 84 kJ usefully. Its efficiency is', '35%', ['29%', '65%', '286%'], r'\(84/240\times100=35\%\).'),
        item('U4 · Organic pathways', 'Converting an alkene to an alcohol directly requires', 'addition of water', ['elimination of water', 'substitution by ammonia', 'oxidation with oxygen only'], 'Hydration adds H and OH across the double bond.'),
        item('U4 · Organic pathways', 'A haloalkane can be converted to a primary amine using', 'ammonia', ['hydrogen gas only', 'a carboxylic acid', 'bromine water'], 'Ammonia substitutes for the halogen.'),
        item('U4 · Peptides', 'A peptide bond forms between amino and carboxyl groups with the loss of', 'water', ['hydrogen gas', 'carbon dioxide', 'ammonia'], 'Peptide formation is a condensation reaction.'),
        item('U4 · Proteins', 'Changing pH far from an enzyme’s optimum can reduce activity because it changes', 'ionic interactions and active-site shape', ['the amino-acid sequence directly', 'the number of peptide bonds', 'the substrate formula'], 'Changed side-chain charges can alter tertiary structure.'),
        item('U4 · Spectroscopy', r'A strong absorption near the carbonyl region in an IR spectrum supports the presence of', r'a \(\mathrm{C=O}\) bond', [r'an \(\mathrm{O-H}\) bond only', 'a metal lattice', 'a neutron'], 'Carbonyl stretching gives a characteristic strong band.'),
        item('U4 · Mass spectrometry', 'Two prominent molecular-ion peaks separated by 2 mass units in an approximate 3:1 ratio suggest the presence of', 'chlorine', ['fluorine', 'oxygen only', 'sodium'], 'The abundant chlorine-35 and chlorine-37 isotopes give this pattern.'),
        item('U4 · NMR spectroscopy', r'An ethyl group commonly gives a proton-NMR pattern containing', 'a triplet and a quartet', ['two singlets only', 'one septet only', 'a doublet and quintet'], 'Neighbouring CH₂ and CH₃ groups split each other by the n+1 rule.'),
        item('U4 · Chromatography', 'In HPLC, peak area is most directly used to estimate', 'amount or concentration of a component', ['molecular geometry', 'oxidation number', 'activation energy'], 'With calibration, detector response area is quantitative.'),
        item('U4 · Green chemistry', 'A reaction with high percentage yield but poor atom economy can still', 'produce substantial stoichiometric waste', ['use every reactant atom in the desired product', 'have zero hazards', 'require no energy'], 'Yield and atom economy measure different aspects.'),
        item('U4 · Experimental design', 'A calibration graph should normally place the measured instrument response on the', 'vertical axis', ['horizontal axis only', 'title', 'uncertainty column'], 'Response is the dependent variable; concentration is controlled.'),
    ])
    return records


def physics_u12():
    records = []
    for frequency, wavelength in ((2.0, 3.0), (5.0, 0.80), (10.0, 0.25), (25.0, 0.12), (4.0, 1.5), (8.0, 0.50)):
        speed = frequency * wavelength
        records.append(item('U1 · Waves and light', f'A wave has frequency {frequency:g} Hz and wavelength {wavelength:g} m. Its speed is', f'{speed:g} m s⁻¹', [f'{frequency/wavelength:g} m s⁻¹', f'{wavelength/frequency:g} m s⁻¹', f'{frequency+wavelength:g} m s⁻¹'], rf'\(v=f\lambda={speed:g}\ \mathrm{{m\ s^{{-1}}}}\).'))
    for resistance, current in ((6, 2.0), (12, 0.50), (8, 1.5), (20, 0.25), (4, 3.0), (10, 0.80)):
        voltage = resistance * current
        records.append(item('U1 · DC circuits', f'A {resistance:g} Ω resistor carries {current:g} A. The potential difference is', f'{voltage:g} V', [f'{resistance/current:g} V', f'{current/resistance:g} V', f'{voltage*10:g} V'], rf'\(V=IR={voltage:g}\ \mathrm V\).'))
    for mass, acceleration in ((2, 3), (5, 1.5), (0.50, 8), (12, 0.25), (3, 4), (8, 2.5)):
        force = mass * acceleration
        records.append(item('U2 AOS1 · Motion', f'An object of mass {mass:g} kg accelerates at {acceleration:g} m s⁻². Its net force is', f'{force:g} N', [f'{mass/acceleration:g} N', f'{mass+acceleration:g} N', f'{force/2:g} N'], rf'\(F_{{net}}=ma={force:g}\ \mathrm N\).'))
    for mass, heat_capacity, rise in ((0.50, 4200, 2), (2.0, 900, 5), (0.25, 450, 8), (1.5, 1000, 4)):
        energy = mass * heat_capacity * rise
        records.append(item('U1 · Thermal energy', f'{mass:g} kg of material with specific heat capacity {heat_capacity:g} J kg⁻¹ K⁻¹ warms by {rise:g} K. Energy transferred is', f'{energy:g} J', [f'{energy/1000:g} J', f'{heat_capacity*rise:g} J', f'{mass*heat_capacity:g} J'], rf'\(Q=mc\Delta T={energy:g}\ \mathrm J\).'))
    for initial, lives in ((800, 2), (640, 3), (1200, 4), (960, 5)):
        remaining = initial / 2**lives
        records.append(item('U1 · Radioactivity', f'A source initially counts {initial} decays per minute. Ignoring background, after {lives} half-lives it counts', f'{remaining:g} decays per minute', [f'{initial/lives:g}', f'{initial/(2*lives):g}', f'{initial-2*lives:g}'], rf'Multiply by \((1/2)^{lives}\).'))
    records.extend([
        item('U1 · Refraction', 'Light entering a medium of larger refractive index bends', 'towards the normal', ['away from the normal', 'along the boundary in every case', 'without changing speed'], 'Its speed falls, so Snell’s law gives a smaller angle.'),
        item('U1 · Electromagnetic spectrum', 'Compared with visible light, ultraviolet radiation has', 'higher frequency and shorter wavelength', ['lower frequency and longer wavelength', 'the same wavelength', 'a slower vacuum speed'], 'All travel at c in vacuum; UV has higher frequency.'),
        item('U1 · Electricity safety', 'An RCD reduces electric-shock risk by detecting', 'a difference between active and neutral currents', ['high appliance power only', 'low supply voltage', 'a warm fuse'], 'An imbalance indicates current leaking to earth.'),
        item('U1 · Voltage dividers', 'In a series voltage divider, the larger resistance has', 'the larger potential difference', ['the smaller potential difference', 'zero current', 'the smaller charge'], 'Series current is common and V=IR.'),
        item('U2 AOS1 · Static structures', 'For an object in translational and rotational equilibrium', 'net force and net torque are both zero', ['speed and acceleration are both zero necessarily', 'momentum is maximum', 'weight equals mass'], 'Both equilibrium conditions must hold.'),
        item('U2 AOS1 · Momentum', 'A longer collision time for the same momentum change produces', 'a smaller average force', ['a larger impulse', 'a larger momentum change', 'zero acceleration'], r'\(F_{avg}=\Delta p/\Delta t\).'),
        item('U2 · Investigation', 'Repeating measurements under unchanged conditions primarily improves knowledge of', 'random variation', ['the true value with certainty', 'the independent variable', 'all systematic errors'], 'Repeated trials show the spread caused by random effects.'),
        item('U2 · Investigation', 'A control variable should be', 'held constant while the independent variable changes', ['measured as the outcome', 'changed with the independent variable', 'removed from the method'], 'Controlling it isolates the tested relationship.'),
    ])
    return records


def physics_u34():
    records = []
    for mass, speed in ((2, 3), (4, 5), (0.50, 8), (3, 6), (10, 2)):
        ke = 0.5 * mass * speed**2
        records.append(item('U3 · Energy and motion', f'A {mass:g} kg object moves at {speed:g} m s⁻¹. Its kinetic energy is', f'{ke:g} J', [f'{ke/2:g} J', f'{ke*2:g} J', f'{ke+mass:g} J'], rf'\(E_k=\tfrac12mv^2={ke:g}\ \mathrm J\).'))
    for mass, speed, radius in ((2, 4, 8), (3, 6, 9), (0.50, 10, 5), (4, 3, 6), (5, 8, 10)):
        force = mass * speed**2 / radius
        records.append(item('U3 · Circular motion', f'A {mass:g} kg object travels at {speed:g} m s⁻¹ in a circle of radius {radius:g} m. The centripetal force is', f'{force:g} N', [f'{force/2:g} N', f'{force*radius:g} N', f'{force+mass:g} N'], rf'\(F=mv^2/r={force:g}\ \mathrm N\).'))
    for mass, initial, final in ((2, 3, 7), (5, -2, 1), (0.5, 8, 2), (4, 0, 6), (3, 5, -1)):
        impulse = mass * (final-initial)
        records.append(item('U3 · Momentum', f'A {mass:g} kg object changes velocity from {initial:g} to {final:g} m s⁻¹. Its impulse is', f'{impulse:g} N s', [f'{impulse/2:g} N s', f'{impulse*2:g} N s', f'{impulse+mass:g} N s'], rf'\(J=m(v-u)={impulse:g}\ \mathrm{{N\ s}}\).'))
    for primary, secondary, vp in ((100, 500, 12), (800, 200, 240), (50, 250, 20), (600, 100, 120)):
        vs = vp * secondary / primary
        records.append(item('U3 · Transformers', f'An ideal transformer has {primary} primary turns, {secondary} secondary turns and primary voltage {vp:g} V. Its secondary voltage is', f'{vs:g} V', [f'{vp*primary/secondary:g} V', f'{vp:g} V', f'{vs/2:g} V'], r'Use \(V_s/V_p=N_s/N_p\).'))
    records.extend([
        item('U3 · Electric fields', 'Between oppositely charged parallel plates away from the edges, the electric field is approximately', 'uniform', ['radially outward', 'zero', 'proportional to distance from the centre'], 'Parallel equipotentials give a nearly uniform field.'),
        item('U3 · Magnetic fields', 'A charged particle moving perpendicular to a uniform magnetic field follows a circular path because the magnetic force', 'is always perpendicular to its velocity', ['does positive work continuously', 'is parallel to velocity', 'changes its charge'], 'The force changes direction but not speed.'),
        item('U3 · Induction', 'Doubling the rate of change of magnetic flux through a coil doubles the magnitude of the induced', 'emf', ['resistance', 'charge on each electron', 'magnetic permeability'], 'Faraday’s law makes emf proportional to flux-change rate.'),
        item('U3 · Relativity', 'A muon lifetime measured in the laboratory exceeds its proper lifetime because of', 'time dilation', ['length expansion', 'classical velocity addition', 'increased rest mass'], 'The moving unstable particle’s clock is observed to run slowly.'),
        item('U3 · Relativity', 'Proper time between two events is measured in the frame where the events occur at', 'the same position', ['the same time only', 'the largest separation', 'light speed'], 'One clock can be present at both events in the proper-time frame.'),
        item('U3 · Relativity', 'No massive object can be accelerated to c because the required energy would', 'increase without bound', ['fall to zero', 'become negative', 'equal its rest energy only'], 'Relativistic energy diverges as speed approaches c.'),
        item('U4 · Wave interference', 'Path difference of one wavelength for two coherent in-phase sources produces', 'constructive interference', ['destructive interference', 'no superposition', 'photoelectric emission'], 'An integer-wavelength path difference preserves phase.'),
        item('U4 · Standing waves', 'A string fixed at both ends in its fundamental mode has length', r'\(\lambda/2\)', [r'\(\lambda\)', r'\(\lambda/4\)', r'\(2\lambda\)'], 'The endpoints are adjacent nodes.'),
        item('U4 · Photoelectric effect', 'Increasing intensity above threshold primarily increases the', 'number of emitted photoelectrons per second', ['maximum kinetic energy', 'work function', 'threshold frequency'], 'More photons arrive, while photon energy hf is unchanged.'),
        item('U4 · Matter waves', 'If a particle’s momentum doubles, its de Broglie wavelength becomes', 'half as large', ['twice as large', 'four times as large', 'unchanged'], r'\(\lambda=h/p\).'),
        item('U4 · Quantum models', 'Electron diffraction is evidence that electrons have', 'wave-like behaviour', ['no momentum', 'only classical trajectories', 'zero charge'], 'A diffraction pattern is a wave phenomenon.'),
        item('U4 · Experimental evidence', 'A model that predicts a straight line should be questioned when residuals show', 'a systematic curved pattern', ['random scatter about zero', 'equal positive and negative values', 'small measurement units'], 'Structure in residuals signals model mismatch.'),
    ])
    return records


def methods_u12_free():
    records = []
    for a, b, x in ((2, 3, 4), (-1, 5, 3), (3, -2, 2), (4, 1, -1), (-2, -3, 5)):
        y = a*x+b
        records.append(item('U1–2 · Functions', rf'For \(f(x)={a}x{b:+d}\), \(f({x})\) is', y, [a+b+x, a*x-b, y+a], 'Substitute the stated input into the rule.'))
    for h, k in ((3, -2), (-4, 1), (2, 5), (-1, -3)):
        records.append(item('U1–2 · Quadratics', rf'The turning point of \(y=(x-{h})^2{k:+d}\) is', rf'\(({h},{k})\)', [rf'\(({-h},{k})\)', rf'\(({h},{-k})\)', rf'\(({k},{h})\)'], 'Read the vertex from completed-square form.'))
    for n, r in ((7, 2), (8, 3), (9, 2), (10, 4), (6, 3)):
        value = comb(n, r)
        records.append(item('U1–2 · Counting and probability', rf'\(\binom{{{n}}}{{{r}}}\) equals', value, [n*r, value+r, max(1, value-r)], 'Use the combinations formula.'))
    for power in (2, 3, 4, 5, 6):
        records.append(item('U1–2 · Differentiation', rf'If \(f(x)=x^{power}\), then \(f\prime(x)=\)', rf'\({power}x^{power-1}\)', [rf'\(x^{power-1}\)', rf'\({power-1}x^{power}\)', rf'\(x^{power+1}/{power+1}\)'], 'Apply the power rule.'))
    records.extend([
        item('U1–2 · Circular functions', r'The exact value of \(\cos(\pi/3)\) is', r'\(1/2\)', [r'\(\sqrt3/2\)', r'\(-1/2\)', '0'], 'Read the unit-circle x-coordinate.'),
        item('U1–2 · Circular functions', r'The vertical asymptotes of \(y=\tan x\) nearest zero occur at', r'\(x=\pm\pi/2\)', [r'\(x=0,\pi\)', r'\(x=\pm\pi\)', r'\(x=\pm\pi/4\)'], 'Cosine is zero at odd multiples of π/2.'),
        item('U1–2 · Exponentials and logarithms', r'The inverse of \(f(x)=3^x\) is', r'\(f^{-1}(x)=\log_3x\)', [r'\(3^{-x}\)', r'\(1/3^x\)', r'\(x^3\)'], 'Logarithm base 3 reverses exponentiation base 3.'),
        item('U1–2 · Exponentials and logarithms', r'\(\log_2 32\) equals', '5', ['4', '16', '64'], r'\(2^5=32\).'),
        item('U1–2 · Probability', r'If \(P(A)=0.4\), then \(P(A^c)=\)', '0.6', ['0.4', '1.4', '0.16'], 'Complementary probabilities sum to one.'),
        item('U1–2 · Probability', 'Two fair coins are tossed. The probability of exactly one head is', r'\(1/2\)', [r'\(1/4\)', r'\(3/4\)', '1'], 'HT and TH are two of four equally likely outcomes.'),
        item('U1–2 · Conditional probability', r'If \(P(A\cap B)=0.18\) and \(P(B)=0.30\), then \(P(A\mid B)=\)', '0.60', ['0.054', '0.48', '1.67'], r'Divide \(P(A\cap B)\) by \(P(B)\).'),
        item('U1–2 · Anti-differentiation', r'An anti-derivative of \(6x^2-4\) is', r'\(2x^3-4x+C\)', [r'\(12x-4+C\)', r'\(2x^3+C\)', r'\(3x^2-4x+C\)'], 'Reverse the power rule term by term.'),
        item('U1–2 · Rates of change', 'On a graph of distance against time, a horizontal segment represents', 'zero speed', ['constant non-zero acceleration', 'negative distance', 'infinite speed'], 'Distance is not changing with time.'),
        item('U1–2 · Transformations', r'From \(y=f(x)\), the graph \(y=-f(x)\) is a reflection in the', 'x-axis', ['y-axis', 'line y=x', 'origin followed by a translation'], 'All output values change sign.'),
    ])
    return records


def methods_u12_active():
    records = []
    for a, root in ((2, 8), (3, 20), (5, 7), (10, 3), (4, 15)):
        answer = f'{root ** (1/a):.3f}'
        records.append(item('U1–2 · Numerical solutions', rf'A numerical solver is used on \(x^{a}={root}\) for \(x>0\). The root to three decimals is', answer, [f'{root/a:.3f}', f'{root**a:.3f}', f'{(root+1)**(1/a):.3f}'], 'Use the positive real root and round only at the end.'))
    for p, trials in ((0.2, 500), (0.35, 1000), (0.08, 2500), (0.6, 200), (0.125, 800)):
        count = int(p*trials)
        records.append(item('U1–2 · Probability simulation', f'A simulation of {trials} trials gives relative frequency {p:g}. The event occurred', f'{count} times', [f'{int((1-p)*trials)} times', f'{int(p*100)} times', f'{trials} times'], 'Count = relative frequency × number of trials.'))
    for x0 in (1.0, 1.5, 2.0, 2.5):
        x1 = (x0 + 5/x0) / 2
        records.append(item('U1–2 · Newton’s method', rf'One Newton step for \(f(x)=x^2-5\) from \(x_0={x0:g}\) gives', f'{x1:.3f}', [f'{x1-0.5:.3f}', f'{x1+0.5:.3f}', f'{x1*2:.3f}'], r'Use \(x_1=x_0-f(x_0)/f\prime(x_0)\).'))
    for a, b in ((1, 6), (2, 8), (3, 12), (4, 20)):
        turning = b*b/(4*a)
        records.append(item('U1–2 · Graphs and technology', rf'The graph \(y=-{a}x^2+{b}x\) has maximum value', f'{turning:g}', [f'{turning-1:g}', f'{turning+1:g}', f'{b/(2*a):g}'], 'Find the vertex, including its y-coordinate.'))
    records.extend([
        item('U1–2 · Graphs and technology', r'A CAS plot of \(y=1/(x-2)\) should show a vertical asymptote at', r'\(x=2\)', [r'\(x=-2\)', r'\(y=2\)', r'\(x=0\)'], 'The denominator is zero at x=2.'),
        item('U1–2 · Newton’s method', 'Newton’s method can fail to approach the intended root when', 'the starting value or local graph behaviour is unsuitable', ['the derivative is written correctly', 'the root is real', 'technology keeps full precision'], 'Iteration depends on tangents and the initial value.'),
        item('U1–2 · Domain and range', r'For \(f(x)=\sqrt{9-x^2}\), the maximal domain is', r'\([-3,3]\)', [r'\(({-3},3)\)', r'\([0,3]\)', r'\mathbb R'], 'Require 9−x² ≥ 0.'),
        item('U1–2 · Composition', r'If \(f(x)=e^x\) and \(g(x)=\ln x\), then \((f\circ g)(4)=\)', '4', [r'\(e^4\)', r'\(\ln4\)', '1'], r'\(e^{\ln4}=4\).'),
        item('U1–2 · Circular modelling', r'A model \(y=3\sin(2t)+5\) has range', r'\([2,8]\)', [r'\([-3,3]\)', r'\([3,5]\)', r'\([{-1},11]\)'], 'Midline 5 plus or minus amplitude 3.'),
        item('U1–2 · Exponential modelling', 'A quantity doubles every 4 hours. After 12 hours its multiplication factor is', '8', ['3', '6', '16'], 'Twelve hours contains three doubling periods.'),
        item('U1–2 · Optimisation', r'The maximum value of \(f(x)=-2x^2+8x-1\) is', '7', ['−1', '4', '15'], 'The vertex is at x=2 and f(2)=7.'),
        item('U1–2 · Technology', 'A numerical graph alone is insufficient to prove that a polynomial has no other roots because', 'the viewing window and sampling can hide features', ['polynomials never have roots', 'CAS outputs are always exact proofs', 'roots cannot be graphed'], 'A complete argument needs an appropriate domain and analytic reasoning.'),
    ])
    return records


def methods_u34_free():
    records = []
    for a, power in ((3, 4), (2, 5), (-1, 6), (4, 3), (5, 2)):
        coefficient = a*power
        records.append(item('U3–4 · Chain rule', rf'\(\frac{{d}}{{dx}}({a}x+1)^{power}=\)', rf'\({coefficient}({a}x+1)^{power-1}\)', [rf'\({power}({a}x+1)^{power-1}\)', rf'\({coefficient}({a}x+1)^{power}\)', rf'\(({a}x+1)^{power-1}\)'], 'Differentiate the outside and multiply by the inner derivative.'))
    for n in (2, 3, 4, 5, 6):
        integral = 1/(n+1)
        records.append(item('U3–4 · Integration', rf'\(\int_0^1 x^{n}\,dx=\)', rf'\(1/{n+1}\)', [rf'\(1/{n}\)', rf'\({n+1}\)', rf'\(1/{(n+1)**2}\)'], rf'\([x^{n+1}/{n+1}]_0^1=1/{n+1}\).'))
    records.extend([
        item('U3–4 · Differentiation', r'\(\frac d{dx}\ln x=\)', r'\(1/x\)', [r'\(\ln x/x\)', r'\(x\)', r'\(e^x\)'], 'This is the standard logarithmic derivative.'),
        item('U3–4 · Differentiation', r'\(\frac d{dx}\sin x=\)', r'\(\cos x\)', [r'\(-\cos x\)', r'\(\sin x\)', r'\(-\sin x\)'], 'Differentiate the circular function.'),
        item('U3–4 · Differentiation', r'\(\frac d{dx}\tan x=\)', r'\(\sec^2x\)', [r'\(\cot x\)', r'\(\sec x\)', r'\(-\csc^2x\)'], 'The derivative of tan is sec².'),
        item('U3–4 · Graph analysis', r'If \(f\prime(x)>0\) and \(f\prime\prime(x)<0\), the graph is', 'increasing and concave down', ['decreasing and concave down', 'increasing and concave up', 'stationary'], 'First derivative gives direction; second derivative gives concavity.'),
        item('U3–4 · Trapezium rule', 'The trapezium rule with more equal subintervals generally', 'improves the approximation for a smooth curve', ['always makes the value exact', 'changes a definite integral into a derivative', 'requires no function values'], 'Narrower trapezia better follow a smooth graph.'),
        item('U3–4 · Probability density', r'For a probability density \(f\), \(\int_{-\infty}^{\infty}f(x)dx=\)', '1', ['0', r'\(\mu\)', r'\(\sigma^2\)'], 'Total probability is one.'),
        item('U3–4 · Binomial distribution', r'If \(X\sim\mathrm{Bi}(20,0.3)\), then \(E(X)=\)', '6', ['14', '4.2', '0.3'], r'\(E(X)=np=20(0.3)=6\).'),
        item('U3–4 · Binomial distribution', r'If \(X\sim\mathrm{Bi}(20,0.3)\), then \(\mathrm{Var}(X)=\)', '4.2', ['6', '14', '2.05'], r'\(np(1-p)=20(0.3)(0.7)=4.2\).'),
        item('U3–4 · Normal distribution', 'For a symmetric normal distribution, the mean and median are', 'equal', ['unrelated', 'opposite', 'both zero in every case'], 'Symmetry centres both measures at μ.'),
        item('U3–4 · Sample proportions', r'For large n, the standard deviation of \(\widehat P\) is', r'\(\sqrt{p(1-p)/n}\)', [r'\(p(1-p)/n\)', r'\(np(1-p)\)', r'\(p/n\)'], 'This is the spread of the sampling distribution.'),
        item('U3–4 · Confidence intervals', 'A 95% confidence interval procedure has the long-run property that', 'about 95% of intervals from repeated samples contain the parameter', ['there is a 95% chance this fixed interval changes', '95% of sample values lie in every interval', 'the parameter varies between samples'], 'Confidence describes repeated-interval coverage.'),
    ])
    return records


def methods_u34_active():
    records = []
    for n, p, k in ((10, 0.2, 0), (8, 0.5, 2), (12, 0.25, 3), (6, 0.4, 1), (15, 0.1, 2)):
        probability = comb(n, k) * p**k * (1-p)**(n-k)
        records.append(item('U3–4 · Binomial probability', rf'For \(X\sim\mathrm{{Bi}}({n},{p:g})\), \(P(X={k})\) to three decimals is', f'{probability:.3f}', [f'{probability/2:.3f}', f'{min(1, probability*2):.3f}', f'{1-probability:.3f}'], 'Use the binomial probability formula or distribution command.'))
    for mean, sd, value in ((40, 5, 50), (70, 8, 54), (100, 15, 115), (25, 2, 20)):
        z = (value-mean)/sd
        records.append(item('U3–4 · Normal distribution', f'For a normal variable with mean {mean} and standard deviation {sd}, the z-score of {value} is', f'{z:g}', [f'{-z:g}', f'{(value-mean):g}', f'{z+1:g}'], r'Use \(z=(x-\mu)/\sigma\), retaining its sign.'))
    records.extend([
        item('U3–4 · Optimisation', r'On \([0,5]\), the absolute maximum of \(f(x)=x(6-x)\) is', '9', ['0', '5', '30'], 'Check the stationary point x=3 and both endpoints.'),
        item('U3–4 · Area between curves', r'The area between \(y=2x\) and \(y=x^2\) from x=0 to x=2 is', r'\(4/3\)', [r'\(2/3\)', r'\(8/3\)', '4'], r'Integrate \(2x-x^2\) from 0 to 2.'),
        item('U3–4 · Differential equations', r'If \(dy/dt=-0.2y\), the quantity is undergoing', 'exponential decay', ['linear growth', 'constant acceleration', 'periodic motion necessarily'], 'The rate is a negative constant multiple of the quantity.'),
        item('U3–4 · Normal distribution', 'A z-score of −1.5 means the observation is', '1.5 standard deviations below the mean', ['1.5 below zero', '1.5 standard deviations above the mean', 'outside every normal model'], 'A negative z-score lies below the mean.'),
        item('U3–4 · Sample proportions', r'For \(p=0.5\) and \(n=100\), the standard deviation of \(\widehat P\) is', '0.05', ['0.005', '0.25', '0.50'], r'\(\sqrt{0.5(0.5)/100}=0.05\).'),
        item('U3–4 · Confidence intervals', 'Holding sample proportion fixed, quadrupling sample size approximately', 'halves the margin of error', ['doubles it', 'quarters it', 'leaves it unchanged'], 'Margin of error scales as 1/√n.'),
        item('U3–4 · Technology', 'When solving an equation numerically on a restricted domain, the domain should be entered because', 'solutions outside it are not valid for the question', ['CAS cannot solve equations otherwise', 'all functions are periodic', 'rounding creates the domain'], 'The stated domain is part of the mathematical problem.'),
    ])
    return records


def specialist_u12_free():
    records = []
    for n in (4, 5, 7, 8, 10):
        edges = n*(n-1)//2
        records.append(item('U1 · Graph theory', rf'The complete graph \(K_{n}\) has', f'{edges} edges', [f'{n} edges', f'{n-1} edges', f'{n*(n-1)} edges'], r'Every pair is joined once: \(n(n-1)/2\).'))
    for a, b in ((2, 3), (3, 4), (5, 2), (4, 5)):
        modulus2 = a*a+b*b
        records.append(item('U2 · Complex numbers', rf'For \(z={a}+{b}i\), \(|z|^2=\)', modulus2, [a+b, abs(a-b), modulus2**2], r'\(|z|^2=a^2+b^2\).'))
    records.extend([
        item('U1 · Logic', r'The contrapositive of \(P\Rightarrow Q\) is', r'\(\neg Q\Rightarrow\neg P\)', [r'\(Q\Rightarrow P\)', r'\(\neg P\Rightarrow\neg Q\)', r'\(P\land Q\)'], 'A statement and its contrapositive are logically equivalent.'),
        item('U1 · Boolean algebra', r'\(P\lor(P\land Q)\) simplifies to', r'\(P\)', [r'\(Q\)', r'\(P\land Q\)', r'\(P\lor Q\)'], 'Apply the absorption law.'),
        item('U1 · Planar graphs', 'For a connected planar graph, Euler’s formula is', r'\(V-E+F=2\)', [r'\(V+E-F=0\)', r'\(V-E=F\)', r'\(V+E+F=2\)'], 'Count the exterior face as well.'),
        item('U1 · Graph theory', 'A graph has an Euler circuit exactly when it is connected apart from isolated vertices and', 'every vertex has even degree', ['exactly two vertices have odd degree', 'every vertex has degree two', 'it has no cycles'], 'An Euler circuit enters and leaves each used vertex in pairs.'),
        item('U1 · Proof', 'To disprove a universal mathematical claim it is sufficient to give', 'one valid counterexample', ['one supporting example', 'a diagram only', 'the converse'], 'A single counterexample makes a universal statement false.'),
        item('U1 · Pigeonhole principle', 'Placing 13 objects into 12 boxes guarantees that', 'some box contains at least two objects', ['every box is occupied', 'one box contains all objects', 'exactly one box is empty'], 'More objects than boxes forces a shared box.'),
        item('U1 · Sequences', r'The sum \(1+2+\cdots+n\) is', r'\(n(n+1)/2\)', [r'\(n(n-1)/2\)', r'\(n^2\)', r'\(2n+1\)'], 'Pair first and last terms or use induction.'),
        item('U2 · Trigonometry', r'\(\sin A\cos B+\cos A\sin B=\)', r'\(\sin(A+B)\)', [r'\(\sin(A-B)\)', r'\(\cos(A+B)\)', r'\(\cos(A-B)\)'], 'Use the sine addition identity.'),
        item('U2 · Vectors', r'The projection of \((3,4)\) onto \((1,0)\) is', r'\((3,0)\)', [r'\((0,4)\)', r'\((3,4)\)', r'\((1,0)\)'], 'Keep the component parallel to the x-axis.'),
        item('U2 · Complex loci', r'The locus \(|z|=3\) is', 'a circle centred at the origin with radius 3', ['a vertical line', 'a disk including its interior', 'a circle centred at 3'], 'Modulus is distance from the origin.'),
    ])
    return records


def specialist_u12_active():
    records = []
    for first, ratio, n in ((2, 3, 5), (5, 2, 6), (3, -2, 4), (4, 0.5, 5)):
        term = first*ratio**(n-1)
        records.append(item('U1 · Sequences', f'A geometric sequence has first term {first:g} and ratio {ratio:g}. Term {n} is', f'{term:g}', [f'{term+first:g}', f'{first+ratio*(n-1):g}', f'{term/ratio:g}'], r'Use \(u_n=u_1r^{n-1}\).'))
    for a, b, c, d in ((2, 1, 3, 2), (4, 1, 2, 1), (3, -1, 2, 5), (1, 3, 2, 4)):
        determinant = a*d-b*c
        records.append(item('U1 · Matrices', rf'The determinant of \(\begin{{pmatrix}}{a}&{b}\\{c}&{d}\end{{pmatrix}}\) is', determinant, [a*d+b*c, a+d, b*c-a*d], 'For a 2×2 matrix, determinant = ad−bc.'))
    for a, b, c, d in ((1, 2, 3, -1), (2, -1, 1, 4), (3, 2, -2, 1), (-1, 3, 2, 2)):
        real = a*c-b*d
        imag = a*d+b*c
        records.append(item('U2 · Complex arithmetic', rf'\(({a}{b:+d}i)({c}{d:+d}i)\) equals', rf'\({real}{imag:+d}i\)', [rf'\({a*c}{b*d:+d}i\)', rf'\({real}{-imag:+d}i\)', rf'\({a+c}{b+d:+d}i\)'], r'Expand and use \(i^2=-1\).'))
    records.extend([
        item('U1 · Matrices', r'If \(A=\begin{pmatrix}1&2\\0&1\end{pmatrix}\), then \(A^2=\)', r'\(\begin{pmatrix}1&4\\0&1\end{pmatrix}\)', [r'\(\begin{pmatrix}1&2\\0&1\end{pmatrix}\)', r'\(\begin{pmatrix}1&4\\0&2\end{pmatrix}\)', r'\(\begin{pmatrix}2&4\\0&2\end{pmatrix}\)'], 'Multiply rows by columns.'),
        item('U1 · Recurrence relations', r'For \(u_{n+1}=0.5u_n+6\), an equilibrium value satisfies', r'\(u=12\)', [r'\(u=6\)', r'\(u=3\)', r'\(u=-12\)'], 'Set consecutive terms equal: u=0.5u+6.'),
        item('U1 · Counting', 'The number of distinct arrangements of the letters in LEVEL is', '30', ['120', '60', '20'], r'\(5!/(2!2!)=30\).'),
        item('U1 · Graph algorithms', 'Breadth-first search on an unweighted graph finds paths with the minimum', 'number of edges', ['total arbitrary edge weight', 'number of vertices in the graph', 'vertex degree'], 'BFS explores vertices layer by layer.'),
        item('U2 · Polar form', r'The complex number \(2(\cos\pi+i\sin\pi)\) equals', '−2', ['2', r'\(2i\)', r'\(-2i\)'], 'At angle π the point is on the negative real axis.'),
        item('U2 · Complex multiplication', 'Multiplication by i rotates a complex number anticlockwise by', r'\(\pi/2\)', [r'\(\pi\)', r'\(-\pi/2\)', r'\(2\pi\)'], 'The argument of i is π/2.'),
        item('U2 · Relative velocity', 'The velocity of A relative to B is', r'\(\vec v_A-\vec v_B\)', [r'\(\vec v_A+\vec v_B\)', r'\(\vec v_B-\vec v_A\)', r'\(\vec v_A\cdot\vec v_B\)'], 'Subtract the reference object’s velocity.'),
        item('U2 · Technology', 'A numerical counterexample found by CAS can', 'disprove a universal claim', ['prove every universal claim', 'replace all definitions', 'establish a converse'], 'One genuine counterexample is logically decisive.'),
    ])
    return records


def specialist_u34_free():
    records = []
    for n in (3, 4, 5, 6):
        records.append(item('U3–4 · Complex numbers', rf'The \({n}\)th roots of unity have successive arguments differing by', rf'\(2\pi/{n}\)', [rf'\(\pi/{n}\)', rf'\({n}\pi\)', rf'\(2\pi/{n+1}\)'], 'The roots are equally spaced around one full revolution.'))
    records.extend([
        item('U3–4 · Mathematical induction', 'After proving the base case, the inductive step assumes the result for n=k and proves it for', r'\(n=k+1\)', [r'\(n=k-1\)', 'all real n directly', 'one unrelated value'], 'This propagates the result through the integers.'),
        item('U3–4 · Complex roots', r'If a real-coefficient polynomial has root \(2+3i\), it also has root', r'\(2-3i\)', [r'\(-2+3i\)', r'\(-2-3i\)', r'\(3+2i\)'], 'Non-real roots of real polynomials occur in conjugate pairs.'),
        item('U3–4 · Implicit differentiation', r'For \(x^2+y^2=25\), \(dy/dx=\)', r'\(-x/y\)', [r'\(x/y\)', r'\(-y/x\)', r'\(2x+2y\)'], 'Differentiate implicitly: 2x+2yy′=0.'),
        item('U3–4 · Integration', r'\(\int\frac{1}{1+x^2}\,dx=\)', r'\(\tan^{-1}x+C\)', [r'\(\ln(1+x^2)+C\)', r'\(\tan x+C\)', r'\(1/(1+x)+C\)'], 'Recognise the inverse-tangent derivative.'),
        item('U3–4 · Differential equations', r'The logistic model \(dy/dt=ky(1-y/M)\) has equilibrium values', r'\(0\) and \(M\)', [r'\(k\) and \(M\)', r'\(0\) only', r'\(M/2\) only'], 'Set the rate equal to zero.'),
        item('U3–4 · Kinematics', r'If \(a=v\,dv/dx\), then integrating with respect to x relates', 'speed and displacement', ['time and mass only', 'force and charge', 'angle and radius only'], 'This derivative form removes time from rectilinear motion.'),
        item('U3–4 · Vector geometry', r'A normal vector to the plane \(3x+2y-z=7\) is', r'\((3,2,-1)\)', [r'\((3,2,7)\)', r'\((1,1,1)\)', r'\((x,y,z)\)'], 'The Cartesian coefficients form a normal.'),
        item('U3–4 · Vector geometry', 'Two planes with parallel non-zero normal vectors are', 'parallel or coincident', ['necessarily perpendicular', 'always distinct', 'skew'], 'Parallel normals give the same plane orientation.'),
        item('U3–4 · Linear combinations', r'For any random variable X, \(\mathrm{Var}(3X-2)=\)', r'\(9\mathrm{Var}(X)\)', [r'\(3\mathrm{Var}(X)-2\)', r'\(9\mathrm{Var}(X)-2\)', r'\(3\mathrm{Var}(X)\)'], 'Shifts do not affect variance; scaling by 3 multiplies variance by 9.'),
        item('U3–4 · Sample means', r'If population mean is \(\mu\), then \(E(\overline X)=\)', r'\(\mu\)', [r'\(\mu/n\)', r'\(n\mu\)', r'\(\sigma/\sqrt n\)'], 'The sample mean is an unbiased estimator of μ.'),
        item('U3–4 · Hypothesis testing', 'A Type I error occurs when a true null hypothesis is', 'rejected', ['not rejected', 'proved', 'replaced before sampling'], 'Type I error is a false rejection.'),
        item('U3–4 · Hypothesis testing', 'For a two-tailed test at level 0.05, the rejection probability under the null is', '0.05 in total across both tails', ['0.10 in each tail', 'zero', '0.95 in each tail'], 'The significance level is shared between the two tails.'),
    ])
    return records


def specialist_u34_active():
    records = []
    for a, b, c, d in ((1, 2, 3, 4), (2, -1, 5, 2), (3, 0, -2, 4), (-1, 3, 2, 1)):
        dot = a*c+b*d
        records.append(item('U3–4 · Vectors', rf'\(({a},{b})\cdot({c},{d})=\)', dot, [dot+1, dot-1, -dot], 'Multiply corresponding components and add.'))
    records.extend([
        item('U3–4 · De Moivre’s theorem', r'\((\cos\theta+i\sin\theta)^4=\)', r'\(\cos4\theta+i\sin4\theta\)', [r'\(4\cos\theta+4i\sin\theta\)', r'\(\cos\theta+i\sin4\theta\)', r'\(\cos(\theta^4)+i\sin(\theta^4)\)'], 'De Moivre multiplies the argument by the integer power.'),
        item('U3–4 · Arc length', r'For \(x=t^2,y=t^3\), the speed with respect to t is', r'\(\sqrt{4t^2+9t^4}\)', [r'\(2t+3t^2\)', r'\(4t^2+9t^4\)', r'\(\sqrt{2t+3t^2}\)'], 'Use the magnitude of the derivative vector.'),
        item('U3–4 · Volumes', r'Rotating \(y=f(x)\ge0\) about the x-axis gives volume element', r'\(\pi[f(x)]^2dx\)', [r'\(2\pi f(x)dx\)', r'\(\pi f(x)dx\)', r'\([f\prime(x)]^2dx\)'], 'Each cross-section is a disk.'),
        item('U3–4 · Direction fields', 'At a point where a direction field has horizontal marks, the differential equation has', r'\(dy/dx=0\)', [r'\(dy/dx=1\)', 'undefined y', 'no solution'], 'Horizontal tangent segments have zero gradient.'),
        item('U3–4 · Vector lines', r'The lines \(\vec r=(1,0,0)+s(1,2,0)\) and \(\vec r=(0,1,1)+t(1,2,0)\) are', 'parallel and distinct', ['intersecting', 'perpendicular', 'the same line'], 'Their directions match, but the displacement between base points is not parallel to it.'),
        item('U3–4 · Vector kinematics', r'If \(\vec r(t)=(t,t^2)\), the velocity at t=2 is', r'\((1,4)\)', [r'\((2,4)\)', r'\((1,2)\)', r'\((0,2)\)'], 'Differentiate each component before substituting.'),
        item('U3–4 · Linear combinations', 'If independent X and Y have standard deviations 2 and 3, the standard deviation of X+Y is', r'\(\sqrt{13}\)', ['5', '13', '1'], 'Add variances, then take the square root.'),
        item('U3–4 · Confidence intervals', r'With \(\bar x=50\), known \(\sigma=10\), \(n=100\) and z=1.96, the interval is', r'\((48.04,51.96)\)', [r'\((40.2,59.8)\)', r'\((49.8,50.2)\)', r'\((30.4,69.6)\)'], r'Margin is \(1.96(10/\sqrt{100})=1.96\).'),
        item('U3–4 · Hypothesis testing', 'A p-value of 0.012 in a test at the 5% level leads to', r'reject \(H_0\)', [r'do not reject \(H_0\)', r'prove \(H_1\)', 'increase the p-value to 0.05'], 'The p-value is below the significance level.'),
        item('U3–4 · Hypothesis testing', 'A one-tailed alternative is appropriate when the research question specifies', 'a direction of change before inspecting data', ['any difference in either direction', 'no population parameter', 'a certain null hypothesis'], 'Direction must come from the question, not the observed sample.'),
    ])
    return records
